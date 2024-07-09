from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from realestate.models import Home
from realestate.serializers import HomeSerializer


@api_view(http_method_names=["POST"])
@permission_classes([IsAuthenticated])
def find_home(request):
    status_code = status.HTTP_400_BAD_REQUEST
    errors = []
    force = request.data.get('force')
    full_address = request.data.get("full_address")
    if full_address is None:
        errors.append("Please provide an address.")
    folder_id = request.data.get("folder_id")
    if folder_id is None:
        errors.append("Please target a specific folder.")

    if len(errors) > 0:
        return Response({"errors": errors}, status=status_code)
    create, result = Home.get_or_create_from_address(
        folder_id=folder_id, full_address=full_address, force=force
    )
    if isinstance(result, str):
        status_code = status.HTTP_404_NOT_FOUND
        response_data = {"error": result}
    else:
        serializer = HomeSerializer(instance=result)
        response_data = serializer.data
        if create:
            status_code = status.HTTP_201_CREATED
        else:
            status_code = status.HTTP_200_OK
    return Response(response_data, status=status_code)


@api_view(http_method_names=["PATCH"])
@permission_classes([IsAuthenticated])
def update_home(request, pk: int):
    home = get_object_or_404(Home.objects.filter(folder__created_by=request.user),
                             pk=pk)
    serializer = HomeSerializer(instance=home, data=request.data, partial=True)
    status_code = status.HTTP_400_BAD_REQUEST
    result = {}
    if serializer.is_valid():
        serializer.save()
        status_code = status.HTTP_200_OK
        result = serializer.data
    return Response(result, status=status_code)
