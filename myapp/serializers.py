from rest_framework import serializers
from .models import Book, BookImage
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re

class BookImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = BookImage
        fields = ['id', 'image']

    def validate_image(self, value):
        max_size = 2 * 1024 * 1024  # 2MB
        if value.size > max_size:
            raise serializers.ValidationError("Image file too large (max 2MB).")
        return value

class BookSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    uploaded_images = BookImageSerializer(source='images', many=True, read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'published_date', 'images', 'uploaded_images']

    def create(self, validated_data):
        image_files = validated_data.pop('images', [])
        book = Book.objects.create(**validated_data)
        for image in image_files:
            BookImage.objects.create(book=book, image=image)
        return book

    def update(self, instance, validated_data):
        image_files = validated_data.pop('images', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if image_files is not None:
            # Delete existing images and add new ones
            instance.images.all().delete()
            for image in image_files:
                BookImage.objects.create(book=instance, image=image)
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    username = serializers.CharField(
        required=True,
        validators=[
            RegexValidator(
                regex=r'^[\w]+$',
                message='Username can only contain letters, numbers, and underscores.'
            )
        ]
    )

    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_password(self, value):
        if value.lower() in ['password', '12345678']:
            raise ValidationError("Password is too common.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        if data['username'].lower() in data['email'].lower():
            raise ValidationError("Username should not be part of the email.")
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user