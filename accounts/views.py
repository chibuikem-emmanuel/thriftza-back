from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    RegisterSerializer, 
    UserSerializer, 
    CustomTokenObtainPairSerializer,
    BulkWhatsAppSerializer
)
from utils.termii import send_termii_whatsapp


class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT Login endpoint."""
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(APIView):
    """Registration endpoint triggering Termii WhatsApp notifications."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            # Send Termii WhatsApp notification
            recipient_phone = user.whatsapp_number or user.phone_number
            if recipient_phone:
                welcome_msg = f"Welcome to GoThriftza, {user.username}! Your account has been successfully created."
                send_termii_whatsapp(recipient_phone, welcome_msg)

            return Response(
                {
                    "message": "User registered successfully",
                    "user": UserSerializer(user).data,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkWhatsAppView(APIView):
    """Admin endpoint to send broadcast messages."""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = BulkWhatsAppSerializer(data=request.data)
        if serializer.is_valid():
            phone_numbers = serializer.validated_data['phone_numbers']
            message = serializer.validated_data['message']
            
            for phone in phone_numbers:
                send_termii_whatsapp(phone, message)

            return Response({"message": "Bulk WhatsApp messages sent successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)