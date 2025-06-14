import json
from decimal import Decimal

from hiero_sdk_python import Client, AccountId, PrivateKey, CryptoGetAccountBalanceQuery, Network
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import FarmerProfile, HederaAccount, CarbonCreditProject, CarbonCreditIssuance, PracticeVerification, \
    VerificationEvidence, SensorData
from .serializers import FarmerProfileSerializer, LoginSerializer, CarbonCreditProjectSerializer, \
    PracticeVerificationSerializer, CarbonCreditIssuanceSerializer, VerificationEvidenceSerializer, SensorDataSerializer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import os
from rest_framework import generics, status
from rest_framework.response import Response
from .models import LandParcel, LandToken, VerificationRequest
from .serializers import (
    LandParcelSerializer,
    VerificationRequestSerializer,
    TokenizationSerializer
)
from .land_verification import LandVerificationService
from .tokenization import LandTokenizationService

User = get_user_model()


class FarmerOnboardingView(generics.CreateAPIView):
    serializer_class = FarmerProfileSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser,)

    def create(self, request, *args, **kwargs):

        data = request.data.copy()

        # data['user'] = json.loads(data['user'])
        data["username"] = data["email"]
        # print(type(data["user"]))

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        farmer = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(farmer)

        hederaaccount = farmer.hederaaccount

        context = {
            'status': 'success',
            'farmer_id': farmer.id,
            'user_id': farmer.user_ptr_id,
            'hedera_account_id': hederaaccount.account_id,
            'did': hederaaccount.did,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }
        return Response(context, status=status.HTTP_201_CREATED)


class GetHederaAccountView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            farmer = request.user.farmerprofile
            hedera_account = farmer.hederaaccount

            # Initialize client to get balance
            client = Client(
                network=Network(os.getenv('HEDERA_NETWORK', 'testnet')),
            )

            operator_id = os.getenv('HEDERA_OPERATOR_ID'),
            operator_key = os.getenv('HEDERA_OPERATOR_PK')
            client.set_operator(AccountId.from_string(operator_id), private_key=PrivateKey.from_string(operator_key))

            balance = CryptoGetAccountBalanceQuery().set_account_id(AccountId.from_string(hedera_account.account_id))

            return Response({
                'account_id': hedera_account.account_id,
                'did': hedera_account.did,
                'balance': balance,
                'did_document': hedera_account.did_document
            })
        except FarmerProfile.DoesNotExist:
            return Response(
                {'error': 'Farmer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        # Get farmer profile and Hedera account info
        try:
            farmer_profile = user.farmerprofile
            hedera_account = farmer_profile.hederaaccount

            # Initialize client to get current balance
            client = Client(network=Network(os.getenv('HEDERA_NETWORK', 'testnet')))
            operator_id = os.getenv('HEDERA_OPERATOR_ID')
            operator_key = os.getenv('HEDERA_OPERATOR_PK')

            client.set_operator(AccountId.from_string(operator_id), PrivateKey.from_string(operator_key))

            balance_query = CryptoGetAccountBalanceQuery().set_account_id(AccountId.from_string(hedera_account.account_id))
            balance = balance_query.execute(client)

            # Update balance in database
            balance_decimal = Decimal(str(balance.hbars).replace(" ℏ", ""))
            hedera_account.account_balance = balance_decimal
            hedera_account.save()
        except FarmerProfile.DoesNotExist:
            hedera_account = None
            balance = 0
            balance_decimal = 0

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'hedera_account_id': hedera_account.account_id if hedera_account else None,
            'did': hedera_account.did if hedera_account else None,
            'balance': balance_decimal
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FarmerProfileSerializer

    def get_object(self):
        return self.request.user.farmerprofile


class LandParcelView(viewsets.ModelViewSet):
    serializer_class = LandParcelSerializer

    def get_queryset(self):
        return LandParcel.objects.filter(farmer_id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        farmer = FarmerProfile.objects.filter(id=request.user.id).first()
        data["farmer"] = farmer
        print(data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class VerificationRequestAPI(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser, JSONParser,)

    def get_queryset(self):
        return VerificationRequest.objects.all()

    def get_serializer_class(self):
        return VerificationRequestSerializer

    def create(self, request, *args, **kwargs):
        print(request.data)
        parcel = LandParcel.objects.get(
            pk=request.data['land_parcel'],
            farmer=request.user.farmerprofile
        )

        # Initiate verification based on method
        method = request.data['verification_method']
        verification_result = None

        if method == 'satellite':
            verification_result = LandVerificationService.verify_with_satellite(parcel)
        elif method == 'gps':
            verification_result = LandVerificationService.verify_with_gps(
                parcel,
                request.data.get('gps_points')
            )
        elif method == 'survey':
            verification_result = LandVerificationService.verify_with_survey(
                parcel,
                request.FILES.get('survey_report')
            )

        # Update parcel status
        if verification_result.get('valid'):
            parcel.verification_status = 'verified'
            parcel.verification_method = method
            parcel.verified_by = request.user
            parcel.save()

        # Create verification request record
        request = VerificationRequest.objects.create(
            land_parcel=parcel,
            requested_by=request.user,
            verification_method=method,
            status='completed' if verification_result.get('valid') else 'failed',
            notes=json.dumps(verification_result)
        )

        return Response({
            "status": request.status,
            "result": verification_result
        }, status=status.HTTP_201_CREATED)


class TokenizeLandAPI(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser, JSONParser,)

    def get_queryset(self):
        return LandToken.objects.all()

    def get_serializer_class(self):
        return TokenizationSerializer

    def create(self, request, *args, **kwargs):
        parcel = LandParcel.objects.get(
            pk=request.data['land_parcel'],
            farmer=request.user.farmerprofile,
            verification_status='verified'
        )

        token_service = LandTokenizationService()
        result = token_service.tokenize_land(parcel)

        # Create land token record
        token = LandToken.objects.create(
            land_parcel=parcel,
            token_id=result['token_id'],
            serial_number=1,
            token_metadata=json.dumps(result['metadata']),
            mint_transaction_id=result['transaction_id']
        )

        return Response({
            "token_id": token.token_id,
            "transaction_id": token.mint_transaction_id,
            "metadata": result['metadata']
        }, status=status.HTTP_201_CREATED)


class CarbonCreditProjectViewSet(viewsets.ModelViewSet):
    queryset = CarbonCreditProject.objects.all()
    serializer_class = CarbonCreditProjectSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = CarbonCreditProjectFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # if self.request.user.is_staff:
        #
        # return self.queryset.filter(farmer__user=self.request.user)
        return self.queryset

    @action(detail=True, methods=['post'])
    def submit_for_approval(self, request, pk=None):
        project = self.get_object()
        if project.status != 'draft':
            return Response(
                {'error': 'Project already submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        project.status = 'submitted'
        project.save()
        return Response({'status': 'submitted for approval'})

    @action(detail=True, methods=['get'])
    def verifications(self, request, pk=None):
        project = self.get_object()
        verifications = project.verifications.all()
        serializer = PracticeVerificationSerializer(verifications, many=True)
        return Response(serializer.data)


class CarbonCreditIssuanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CarbonCreditIssuance.objects.all()
    serializer_class = CarbonCreditIssuanceSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = CarbonCreditIssuanceFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(project__farmer_id=self.request.user.id)


class PracticeVerificationViewSet(viewsets.ModelViewSet):
    queryset = PracticeVerification.objects.all()
    serializer_class = PracticeVerificationSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = PracticeVerificationFilter
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(verified_by=self.request.user)


class VerificationEvidenceViewSet(viewsets.ModelViewSet):
    queryset = VerificationEvidence.objects.all()
    serializer_class = VerificationEvidenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        verification_id = self.request.data.get('verification')
        verification = PracticeVerification.objects.get(pk=verification_id)
        if not (self.request.user.is_staff or verification.project.farmer.user == self.request.user):
            raise PermissionDenied("You don't have permission to add evidence to this verification")
        serializer.save()


class SensorDataViewSet(viewsets.ModelViewSet):
    queryset = SensorData.objects.all()
    serializer_class = SensorDataSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = SensorDataFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(project__farmer__user=self.request.user)
