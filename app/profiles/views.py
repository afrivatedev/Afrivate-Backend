"""
The profile app handles things like the pathfinder and Enabler view as well as
government issued identifications for both pathfinder and Enabler.
"""
from rest_framework import (
viewsets,
mixins,
status
)


class ProfileView(viewsets.ModelViewSet):
    """a model viewset to handle CRUD operations on the profile model"""
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer