from rest_framework import views
from rest_framework.response import Response


class NagadCreatePaymentView(views.APIView):
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Nagad Payment Account Not Found!"
            }
        )
    
