import json
import os

from django.conf import settings
from hiero_sdk_python import TokenCreateTransaction, TokenMintTransaction, Client, Network, AccountId, PrivateKey
from hiero_sdk_python.hapi.services.basic_types_pb2 import TokenType, TokenSupplyType

from farmer.models import HederaAccount


class LandTokenizationService:

    def tokenize_land(self, land_parcel):
        hedera_account = HederaAccount.objects.filter(farmer_id=land_parcel.farmer_id).first()

        client = Client(network=Network(os.getenv('HEDERA_NETWORK', 'testnet')))
        operator_id = os.getenv('HEDERA_OPERATOR_ID')
        operator_key = os.getenv('HEDERA_OPERATOR_PK')
        client.set_operator(AccountId.from_string(operator_id), PrivateKey.from_string(operator_key))

        admin_key = PrivateKey.from_string(os.getenv('HEDERA_OPERATOR_PK'))  # Optional not necessarily HEDERA_OPERATOR_PK but has to be hex
        supply_key = PrivateKey.from_string(os.getenv('HEDERA_OPERATOR_PK'))  # Optional
        payer_key = PrivateKey.from_string(os.getenv('HEDERA_OPERATOR_PK'))  # Optional

        """Create NFT for verified land parcel"""
        # 1. Prepare metadata
        metadata = {
            "title": f"Land Parcel #{land_parcel.id}",
            "deed_number": land_parcel.title_deed_number,
            "area_ha": float(land_parcel.total_area),
            # "location": {
            #     "address": land_parcel.address,
            #     "country": land_parcel.country,
            #     "region": land_parcel.region,
            #     "coordinates": json.loads(land_parcel.gps_coordinates)
            # },
            # "verification": {
            #     "status": land_parcel.verification_status,
            #     "method": land_parcel.verification_method,
            #     "date": land_parcel.verification_date.isoformat() if land_parcel.verification_date else None
            # }
        }

        # 2. Create NFT token
        token_create_tx = (
            TokenCreateTransaction()
            .set_token_name(f"LAND-{land_parcel.id}")
            .set_token_symbol("LAND")
            .set_decimals(0)
            .set_initial_supply(0)
            .set_supply_key(supply_key)
            .set_admin_key(admin_key)
            # .set_token_type(TokenType.NON_FUNGIBLE_UNIQUE)
            # .set_supply_type(TokenSupplyType.FINITE)
            # .set_max_supply(100)
            .set_treasury_account_id(AccountId.from_string(operator_id))
            .freeze_with(client)
        )

        opk = PrivateKey.from_string(os.getenv('HEDERA_OPERATOR_PK'))

        token_create_tx.sign(opk)

        token_create_receipt = token_create_tx.execute(client)
        token_id = token_create_receipt.tokenId
        # token_id = token_tx.getReceipt(client).tokenId

        # 3. Mint NFT with metadata
        json_dump = json.dumps(metadata).encode()
        print(json_dump)
        token_mint_tx = (
            TokenMintTransaction()
            .set_token_id(token_id)
            # .set_amount(1000)
            .set_metadata(json_dump)
            .freeze_with(client)
            .sign(supply_key)
        )
        token_mint_receipt = token_mint_tx.execute(client)
        print(token_mint_receipt.to_proto())
        return {
            "token_id": str(token_id),
            "transaction_id": str(token_mint_receipt),
            "metadata": metadata
        }