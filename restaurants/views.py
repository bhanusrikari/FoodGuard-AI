from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from restaurants.models import Restaurant
from restaurants.permissions import (
    RestaurantDetailPermission,
    RestaurantListCreatePermission,
)
from restaurants.serializers import (
    RestaurantCreateSerializer,
    RestaurantReadSerializer,
    RestaurantUpdateSerializer,
)

# Fields that only REVIEWER / ADMIN may set via PATCH
_RESTRICTED_UPDATE_FIELDS = {"is_verified"}
_PRIVILEGED_ROLES = {User.Role.REVIEWER, User.Role.ADMIN}


@extend_schema_view(
    get=extend_schema(responses={200: RestaurantReadSerializer(many=True)}),
    post=extend_schema(request=RestaurantCreateSerializer, responses={201: RestaurantReadSerializer, 400: dict}),
)
class RestaurantListCreateView(APIView):
    """
    GET  /api/v1/restaurants/   — list all active restaurants (authenticated)
    POST /api/v1/restaurants/   — create a restaurant (RESTAURANT_USER or ADMIN)
    """

    permission_classes = [RestaurantListCreatePermission]

    def get(self, request: Request) -> Response:
        restaurants = Restaurant.objects.select_related("owner").filter(
            is_active=True
        )
        serializer = RestaurantReadSerializer(restaurants, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        # Extra guard: RESTAURANT_USER can only create for themselves
        # (owner is injected from JWT — not from payload)
        serializer = RestaurantCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        restaurant = serializer.save()
        return Response(
            RestaurantReadSerializer(restaurant).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses={200: RestaurantReadSerializer, 404: dict}),
    patch=extend_schema(request=RestaurantUpdateSerializer, responses={200: RestaurantReadSerializer, 400: dict, 403: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 404: dict}),
)
class RestaurantDetailView(APIView):
    """
    GET    /api/v1/restaurants/<id>/  — retrieve restaurant
    PATCH  /api/v1/restaurants/<id>/  — partial update
    DELETE /api/v1/restaurants/<id>/  — delete
    """

    permission_classes = [RestaurantDetailPermission]

    def _get_object(self, pk: int) -> Restaurant | None:
        try:
            return Restaurant.objects.select_related("owner").get(pk=pk)
        except Restaurant.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        restaurant = self._get_object(pk)
        if restaurant is None:
            return Response(
                {"detail": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, restaurant)
        serializer = RestaurantReadSerializer(restaurant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, pk: int) -> Response:
        restaurant = self._get_object(pk)
        if restaurant is None:
            return Response(
                {"detail": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, restaurant)

        # Block RESTAURANT_USER from setting is_verified
        incoming_fields = set(request.data.keys())
        restricted_attempted = incoming_fields & _RESTRICTED_UPDATE_FIELDS
        if restricted_attempted and request.user.role not in _PRIVILEGED_ROLES:
            return Response(
                {
                    "detail": (
                        "You are not permitted to change: "
                        + ", ".join(sorted(restricted_attempted))
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RestaurantUpdateSerializer(
            restaurant, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        updated = serializer.save()
        return Response(
            RestaurantReadSerializer(updated).data, status=status.HTTP_200_OK
        )

    def delete(self, request: Request, pk: int) -> Response:
        restaurant = self._get_object(pk)
        if restaurant is None:
            return Response(
                {"detail": "Restaurant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, restaurant)
        restaurant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
