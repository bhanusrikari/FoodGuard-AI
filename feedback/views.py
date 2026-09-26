from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from feedback.models import Feedback
from feedback.permissions import FeedbackDetailPermission, FeedbackListCreatePermission
from feedback.serializers import FeedbackCreateSerializer, FeedbackReadSerializer
from feedback.services import FeedbackError

_PRIVILEGED_ROLES = {User.Role.REVIEWER, User.Role.ADMIN}


@extend_schema_view(
    get=extend_schema(responses={200: FeedbackReadSerializer(many=True)}),
    post=extend_schema(request=FeedbackCreateSerializer, responses={201: FeedbackReadSerializer, 400: dict}),
)
class FeedbackListCreateView(APIView):
    """
    GET  /api/v1/feedback/  — list feedback (role-filtered)
    POST /api/v1/feedback/  — create feedback (CUSTOMER only)
    """

    permission_classes = [FeedbackListCreatePermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request: Request) -> Response:
        role = request.user.role
        if role in _PRIVILEGED_ROLES:
            qs = Feedback.objects.select_related("complaint", "customer").all()
        else:
            # CUSTOMER sees only their own; RESTAURANT_USER sees nothing here
            qs = Feedback.objects.select_related(
                "complaint", "customer"
            ).filter(customer=request.user)

        serializer = FeedbackReadSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        serializer = FeedbackCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            feedback = serializer.save()
        except FeedbackError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            FeedbackReadSerializer(feedback).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses={200: FeedbackReadSerializer, 404: dict}),
)
class FeedbackDetailView(APIView):
    """
    GET /api/v1/feedback/<id>/

    Create-and-read-only design — no PATCH or DELETE endpoints.
    """

    permission_classes = [FeedbackDetailPermission]

    def _get_object(self, pk: int):
        try:
            return Feedback.objects.select_related(
                "complaint", "customer"
            ).get(pk=pk)
        except Feedback.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        feedback = self._get_object(pk)
        if feedback is None:
            return Response(
                {"detail": "Feedback not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, feedback)
        return Response(
            FeedbackReadSerializer(feedback).data,
            status=status.HTTP_200_OK,
        )
