import datetime
import json

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from hiero_sdk_python import Client, AccountId, PrivateKey, Network, AccountCreateTransaction, Hbar, ResponseCode
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import FarmerProfile, HederaAccount, LandParcel, VerificationRequest
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
import os
from dotenv import load_dotenv
from .utils import get_crypto
load_dotenv()  # Load environment variables


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                return user
            raise serializers.ValidationError("Unable to log in with provided credentials.")
        raise serializers.ValidationError("Must include 'username' and 'password'.")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Use create_user to hash the password
        return User.objects.create_user(**validated_data)


class FarmerProfileSerializer(serializers.ModelSerializer):
    # user = UserSerializer()
    id_document = serializers.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        required=True
    )

    class Meta:
        model = FarmerProfile
        fields = [
            "id_document", "first_name", "last_name", "email", "username", "phone_number", "date_of_birth",
            "government_id_number", "physical_address", "country", "region", "password"
        ]
        read_only_fields = ['is_verified', 'verification_date']

    def validate_government_id_number(self, value):
        if not value.isalnum():
            raise ValidationError("ID number must be alphanumeric")
        return value

    def create(self, validated_data):
        # user_data = validated_data.pop('user')
        # user = User.objects.create_user(**user_data)

        # Initialize Hiero Hedera Client
        client = Client(network=Network(os.getenv('HEDERA_NETWORK', 'testnet')))
        operator_id = os.getenv('HEDERA_OPERATOR_ID')
        operator_key = os.getenv('HEDERA_OPERATOR_PK')
        # print(operator_id, operator_key)
        client.set_operator(AccountId.from_string(operator_id), PrivateKey.from_string(operator_key))

        # Generate key for the new farmer wallet
        new_private_key = PrivateKey.generate("ed25519")
        new_public_key = new_private_key.public_key()

        # Create the Hedera account with 1 HBAR (100_000_000 tinybars)
        tx = AccountCreateTransaction().set_key(new_public_key).set_initial_balance(100_000_000)

        receipt = tx.execute(client=client)
        # receipt = tx_response.get_receipt(client)
        if receipt.status != ResponseCode.SUCCESS:
            status_message = ResponseCode.get_name(receipt.status)
            raise Exception(f"Transaction failed with status: {status_message}")

        new_account_id = receipt.accountId

        # Optional: simulate DID registration (you can implement this)
        did_document = {
            "id": f"did:hedera:{new_account_id}",
            "type": "FarmerIdentity",
            "owner": f"{validated_data['first_name']} {validated_data['last_name']}",
            "created": datetime.datetime.utcnow().isoformat()
        }
        validated_data['password'] = make_password(validated_data['password'])

        # Create Farmer Profile
        print(validated_data)
        profile = FarmerProfile.objects.create(**validated_data)

        # Store Hedera account securely
        crypto = get_crypto()
        HederaAccount.objects.create(
            farmer=profile,
            account_id=str(new_account_id),
            public_key=crypto.encrypt(new_public_key.to_string()),
            private_key=crypto.encrypt(new_private_key.to_string()),
            did=did_document['id'],
            did_document=did_document
        )

        return profile


class LandParcelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandParcel
        fields = '__all__'
        read_only_fields = [
            'verification_status',
            'verification_method',
            'verification_date',
            'verified_by',
            'ipfs_hash'
        ]

    def validate_gps_coordinates(self, value):
        try:
            coords = json.loads(value)
            if not isinstance(coords, list) or len(coords) < 3:
                raise serializers.ValidationError("At least 3 coordinates required")
            return value
        except json.JSONDecodeError:
            raise serializers.ValidationError("Invalid JSON format")


class VerificationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationRequest
        fields = '__all__'
        read_only_fields = ['requested_by', 'request_date', 'status']


class TokenizationSerializer(serializers.Serializer):
    land_parcel = serializers.PrimaryKeyRelatedField(
        queryset=LandParcel.objects.filter(verification_status='verified')
    )