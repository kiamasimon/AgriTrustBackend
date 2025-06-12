from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models


class FarmerProfile(get_user_model()):
    # user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    government_id_number = models.CharField(max_length=50, null=True, blank=True)
    id_document = models.FileField(upload_to='kyc_documents/', null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    physical_address = models.TextField()
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def hederaaccount(self):
        return HederaAccount.objects.filter(farmer_id=self.id).first()


class HederaAccount(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=50)
    public_key = models.TextField()  # Encrypted
    private_key = models.TextField()  # Encrypted
    did = models.CharField(max_length=200, blank=True, null=True)
    did_document = models.JSONField(blank=True, null=True)
    account_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    last_balance_check = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LandParcel(models.Model):
    farmer = models.ForeignKey(FarmerProfile, related_name="land_owner", on_delete=models.CASCADE)
    title_deed_number = models.CharField(max_length=100, null=True, blank=True)
    title_deed_document = models.FileField(upload_to='title_deeds/', null=True, blank=True)
    total_area = models.DecimalField(max_digits=10, decimal_places=2)  # in hectares
    gps_coordinates = models.TextField()  # JSON of polygon coordinates
    address = models.TextField()
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('unverified', 'Unverified'),
            ('pending', 'Pending Verification'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected')
        ],
        default='unverified'
    )
    verification_method = models.CharField(
        max_length=20,
        choices=[
            ('satellite', 'Satellite Imagery'),
            ('survey', 'Professional Survey'),
            ('gps', 'GPS Measurement'),
            ('manual', 'Manual Verification')
        ],
        null=True,
        blank=True
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ipfs_hash = models.CharField(max_length=100, null=True, blank=True)  # For land documents storage
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LandToken(models.Model):
    land_parcel = models.OneToOneField(LandParcel, on_delete=models.CASCADE)
    token_id = models.CharField(max_length=50)  # Hedera token ID
    serial_number = models.IntegerField()  # For NFT serials
    token_metadata = models.TextField()  # JSON metadata
    mint_transaction_id = models.CharField(max_length=100)  # Hedera transaction ID
    mint_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class CarbonCreditProject(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    land_parcel = models.ForeignKey(LandParcel, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=200)
    project_description = models.TextField()
    methodology = models.CharField(
        max_length=50,
        choices=[
            ('agroforestry', 'Agroforestry'),
            ('conservation_ag', 'Conservation Agriculture'),
            ('organic', 'Organic Farming'),
            ('reforestation', 'Reforestation')
        ]
    )
    start_date = models.DateField()
    verification_standard = models.CharField(
        max_length=50,
        choices=[
            ('verra', 'Verra'),
            ('gold_standard', 'Gold Standard'),
            ('acr', 'American Carbon Registry'),
            ('custom', 'Custom Methodology')
        ]
    )
    is_approved = models.BooleanField(default=False)
    approved_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CarbonCreditIssuance(models.Model):
    project = models.ForeignKey(CarbonCreditProject, on_delete=models.CASCADE)
    issuance_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # in tons of CO2 equivalent
    token_id = models.CharField(max_length=50)  # Hedera token ID
    batch_number = models.CharField(max_length=50)
    verification_report = models.FileField(upload_to='verification_reports/')
    verification_body = models.CharField(max_length=200)
    transaction_id = models.CharField(max_length=100)  # Hedera transaction ID
    is_retired = models.BooleanField(default=False)
    retired_date = models.DateTimeField(null=True, blank=True)


class SensorData(models.Model):
    project = models.ForeignKey(CarbonCreditProject, on_delete=models.CASCADE)
    sensor_type = models.CharField(
        max_length=50,
        choices=[
            ('soil_moisture', 'Soil Moisture'),
            ('temperature', 'Temperature'),
            ('rainfall', 'Rainfall'),
            ('ndvi', 'NDVI (Vegetation Index)')
        ]
    )
    value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    reading_date = models.DateTimeField()
    source = models.CharField(
        max_length=50,
        choices=[
            ('iot_device', 'IoT Device'),
            ('satellite', 'Satellite'),
            ('manual', 'Manual Entry')
        ]
    )
    device_id = models.CharField(max_length=100, null=True, blank=True)
    is_verified = models.BooleanField(default=False)


# Sustainable practice records
class PracticeVerification(models.Model):
    project = models.ForeignKey(CarbonCreditProject, on_delete=models.CASCADE)
    verification_date = models.DateField()
    verification_type = models.CharField(
        max_length=50,
        choices=[
            ('remote', 'Remote Sensing'),
            ('field_visit', 'Field Visit'),
            ('farmer_report', 'Farmer Report'),
            ('community', 'Community Verification')
        ]
    )
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    findings = models.TextField()
    is_compliant = models.BooleanField()
    evidence_documents = models.FileField(upload_to='verification_evidence/', null=True, blank=True)
    photos = models.FileField(upload_to='verification_photos/', null=True, blank=True)


class TransactionHistory(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100)
    transaction_type = models.CharField(
        max_length=50,
        choices=[
            ('account_create', 'Account Creation'),
            ('land_tokenize', 'Land Tokenization'),
            ('credit_issuance', 'Carbon Credit Issuance'),
            ('credit_transfer', 'Credit Transfer'),
            ('credit_retire', 'Credit Retirement')
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed')
        ]
    )
    timestamp = models.DateTimeField()
    details = models.JSONField()  # Raw transaction details
    network_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


class VerificationRequest(models.Model):
    land_parcel = models.ForeignKey(LandParcel, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    verification_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='pending')
    completed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)


class Device(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    device_id = models.CharField(max_length=100, unique=True)
    device_type = models.CharField(max_length=100)
    installation_date = models.DateField()
    last_maintenance = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    location = models.TextField(null=True, blank=True)