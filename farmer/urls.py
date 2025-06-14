from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import FarmerOnboardingView, GetHederaAccountView, LoginView, UserProfileView, LandParcelView


app_name = "Farmer"
router = DefaultRouter()
router.register(r'land/verification', views.VerificationRequestAPI, basename='VerificationRequestAPI')
router.register(r'land/tokenize', views.TokenizeLandAPI, basename='TokenizeLandAPI')
router.register(r'land', views.LandParcelView, basename='LandParcelView')

router.register(r'projects', views.CarbonCreditProjectViewSet, basename='CarbonCreditProjectViewSet')
router.register(r'issuances', views.CarbonCreditIssuanceViewSet, basename='CarbonCreditIssuanceViewSet')
router.register(r'verifications', views.PracticeVerificationViewSet, basename='PracticeVerificationViewSet')
router.register(r'evidence', views.VerificationEvidenceViewSet, basename='VerificationEvidenceViewSet')
router.register(r'sensor-data', views.SensorDataViewSet, basename='SensorDataViewSet')

urlpatterns = [
    path('register/', FarmerOnboardingView.as_view(), name='farmer-register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('hedera-account/', GetHederaAccountView.as_view(), name='hedera-account'),
    path('', include(router.urls)),
]