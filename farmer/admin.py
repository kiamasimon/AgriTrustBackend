from django.contrib import admin
from .models import FarmerProfile, HederaAccount, LandParcel, VerificationRequest, LandToken, CarbonCreditProject

admin.site.register(FarmerProfile)
admin.site.register(HederaAccount)
admin.site.register(LandParcel)
admin.site.register(VerificationRequest)
admin.site.register(LandToken)
admin.site.register(CarbonCreditProject)