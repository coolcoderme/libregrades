from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.server_identity import server_info_payload


class ServerInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(server_info_payload())
