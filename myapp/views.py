from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Book
from .serializers import BookSerializer, UserSerializer, RegisterSerializer
from django.contrib.auth.models import User
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import AccessToken

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh_token = response.data['refresh']
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite='Strict',
            max_age=86400  # 1 day (match REFRESH_TOKEN_LIFETIME)
        )
        del response.data['refresh']  # Remove from JSON response
        return response
    
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Get the refresh token from the cookie
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({'detail': 'Refresh token missing.'}, status=status.HTTP_400_BAD_REQUEST)

        # Set the refresh token in the request data for simplejwt to process
        request.data['refresh'] = refresh_token

        # Call the parent class to refresh the token
        response = super().post(request, *args, **kwargs)

        # Get the new refresh token from the response
        new_refresh_token = response.data.get('refresh')
        if new_refresh_token:
            # Update the cookie with the new refresh token
            response.set_cookie(
                'refresh_token',
                new_refresh_token,
                httponly=True,
                secure=True,  # Set to True in production with HTTPS
                samesite='Strict',
                max_age=86400  # 1 day (match REFRESH_TOKEN_LIFETIME)
            )
            # Remove the refresh token from the JSON response
            del response.data['refresh']

        return response

class BookListCreateView(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    parser_classes = [MultiPartParser, FormParser]  
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['title', 'author', 'published_date']  # Fields to filter on
    search_fields = ['title', 'author']  # Fields to search in
    ordering_fields = ['title', 'author', 'published_date']  # Fields to sort by

class BookDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    parser_classes = [MultiPartParser, FormParser]

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]  # Allow anyone to register

class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user  # Return the authenticated user
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                refresh = RefreshToken(refresh_token)
                refresh.blacklist()

            # Optionally blacklist the access token
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]
                try:
                    AccessToken(access_token).blacklist()
                except Exception:
                    pass  # Ignore if token is invalid or already expired

            response = Response(status=status.HTTP_205_RESET_CONTENT)
            response.delete_cookie(
                'refresh_token',
                path='/',
                domain=None
            )
            return response
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)