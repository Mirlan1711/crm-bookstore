from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        identifier = (attrs.get("username") or "").strip()
        user = User.objects.filter(username__iexact=identifier).first()
        if user is None:
            user = User.objects.filter(email__iexact=identifier).first()
        if user is not None:
            attrs["username"] = user.username
        return super().validate(attrs)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password_confirm", "first_name", "last_name")

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
        return attrs

    def validate_email(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "phone", "is_staff", "is_active", "permissions")
        read_only_fields = ("id", "username", "role", "is_staff", "is_active")

    def get_permissions(self, obj):
        return UserManagementSerializer.permission_map().get(obj.role, [])


class UserManagementSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=False)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password_confirm", "first_name", "last_name", "role", "phone", "is_staff", "is_active", "permissions")
        read_only_fields = ("id", "is_staff")

    @staticmethod
    def permission_map():
        return {
            "admin": ["Все разделы", "Пользователи и роли", "Настройки и справочники"],
            "supervisor": ["Просмотр всех данных", "Dashboard и отчёты", "Настройка CRM"],
            "manager": ["Клиенты", "Заказы", "Задачи"],
            "user": ["Назначенные задачи"],
        }

    def get_permissions(self, obj):
        return self.permission_map().get(obj.role, [])

    def validate(self, attrs):
        password = attrs.pop("password", None)
        password_confirm = attrs.pop("password_confirm", None)
        if self.instance is None:
            if not password:
                raise serializers.ValidationError({"password": "Укажите пароль сотрудника."})
            if password != password_confirm:
                raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
            attrs["_password"] = password
        elif password:
            if password != password_confirm:
                raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
            attrs["_password"] = password
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("_password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("_password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "Текущий пароль указан неверно."})
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Пароли не совпадают."})
        return attrs

