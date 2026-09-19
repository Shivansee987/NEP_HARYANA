from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from .utils import decode_token

User = get_user_model()

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise exceptions.AuthenticationFailed('Authorization header must be Bearer <token>')
            
        access_token = parts[1]
        
        payload = decode_token(access_token)
        if not payload:
            raise exceptions.AuthenticationFailed('Invalid or expired access token')
            
        user_id = payload.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Token lacks user ID')
            
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')
            
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User account is disabled')
            
        return (user, None)

    def authenticate_header(self, request):
        return 'Bearer'
