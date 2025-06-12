from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)

        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        validated_token = self.get_validated_token(raw_token)

        try:
            user_id = validated_token['user_id']
            user = User.objects.get(pk=user_id, is_active=True)
            return user, validated_token
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')