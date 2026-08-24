from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'whatsapp_number')


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Allows login with either Username OR Email and returns user profile."""

    def validate(self, attrs):
        username_or_email = attrs.get("username")

        # Check if login input is an email address
        if username_or_email and "@" in username_or_email:
            try:
                user_obj = User.objects.get(email__iexact=username_or_email)
                attrs["username"] = user_obj.username
            except User.DoesNotExist:
                pass  # Let SimpleJWT raise standard authentication error

        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    whatsapp_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'whatsapp_number', 'password', 'full_name')
        extra_kwargs = {
            'username': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
            'phone_number': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        raw_username = validated_data.get('username')
        full_name = validated_data.get('full_name', '')
        email = validated_data.get('email', '')
        phone = validated_data.get('phone_number', '')
        whatsapp = validated_data.get('whatsapp_number') or phone

        # Auto-generate username from full_name or email if blank
        if not raw_username or not raw_username.strip():
            if full_name:
                raw_username = full_name.lower().replace(" ", "_")
            elif email:
                raw_username = email.split('@')[0]
            else:
                raw_username = "user"

        # Prevent username conflicts
        username = raw_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{raw_username}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            phone_number=phone,
            whatsapp_number=whatsapp,
            password=validated_data['password'],
        )
        return user


class BulkWhatsAppSerializer(serializers.Serializer):
    phone_numbers = serializers.ListField(
        child=serializers.CharField(max_length=20),
        allow_empty=False
    )
    message = serializers.CharField(max_length=1000)