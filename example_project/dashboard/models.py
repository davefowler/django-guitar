"""
Dashboard models demonstrating Django Guitar's Model-Level Security (MLS).

This example implements a collaborative dashboard application with role-based access:

Roles & Permissions:
| Role      | Dashboard           | Charts                      | Invite Users |
|-----------|--------------------|-----------------------------|--------------|
| creator   | create, read, update, delete | create, read, update, delete | ✓ |
| editor    | read, update       | create, read, update, delete | ✗ |
| viewer    | read               | read                        | ✗ |
"""

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from guitar import GuitarModel


class Dashboard(GuitarModel, models.Model):
    """
    A dashboard that can contain multiple charts.
    Access is controlled via DashboardMembership roles.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # M2M with role via through table
    members = models.ManyToManyField(
        User,
        through='DashboardMembership',
        through_fields=('dashboard', 'user'),
        related_name='dashboards',
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return self.name
    
    class GuitarMeta:
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        writable_fields = ['name', 'description']
        read_only_fields = ['id', 'created_at', 'updated_at']
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        filterable_fields = ['id', 'name', 'created_at']
        orderable_fields = ['name', 'created_at', 'updated_at']
        searchable_fields = ['name', 'description']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Users can see dashboards they're a member of."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(members=request.user).distinct()
        
        def filter_write(self, request, queryset):
            """Only creators and editors can update dashboards."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                dashboardmembership__user=request.user,
                dashboardmembership__role__in=['creator', 'editor'],
            ).distinct()
        
        def filter_delete(self, request, queryset):
            """Only creators can delete dashboards."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                dashboardmembership__user=request.user,
                dashboardmembership__role='creator',
            ).distinct()
        
        def check_create(self, request, data):
            """Anyone can create a dashboard (they become the creator)."""
            return data
        
        def post_create(self, request, instance):
            """Auto-add creator as member with 'creator' role."""
            DashboardMembership.objects.create(
                user=request.user,
                dashboard=instance,
                role='creator',
            )


class DashboardMembership(GuitarModel, models.Model):
    """
    Through table for Dashboard <-> User with role.
    Controls who can access a dashboard and what they can do.
    """
    ROLE_CHOICES = [
        ('creator', 'Creator'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    invited_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invitations_sent',
    )
    
    class Meta:
        unique_together = ['user', 'dashboard']
        ordering = ['-invited_at']
    
    def __str__(self) -> str:
        return f"{self.user.username} - {self.dashboard.name} ({self.role})"
    
    class GuitarMeta:
        fields = ['id', 'user_id', 'dashboard_id', 'role', 'invited_at', 'invited_by_id']
        writable_fields = ['user_id', 'dashboard_id', 'role']
        read_only_fields = ['id', 'invited_at', 'invited_by_id']
        exclude_operations = ['update']  # Can only create or delete memberships
        filterable_fields = ['dashboard_id', 'user_id', 'role']
    
    class GuitarManager:
        chain_permissions = True
        
        def filter_read(self, request, queryset):
            """Can see memberships for dashboards you're a member of."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(dashboard__members=request.user).distinct()
        
        def filter_delete(self, request, queryset):
            """Only creators can remove members."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                dashboard__dashboardmembership__user=request.user,
                dashboard__dashboardmembership__role='creator',
            ).exclude(
                # Can't remove yourself if you're the only creator
                user=request.user,
                role='creator',
            ).distinct()
        
        def check_create(self, request, data):
            """Only creators can invite new members."""
            dashboard_id = data.get('dashboard_id')
            
            is_creator = DashboardMembership.objects.filter(
                user=request.user,
                dashboard_id=dashboard_id,
                role='creator',
            ).exists()
            
            if not is_creator:
                raise PermissionDenied("Only creators can invite members")
            
            data['invited_by_id'] = request.user.id
            return data


class Chart(GuitarModel, models.Model):
    """
    A chart within a dashboard.
    Access is controlled via the parent dashboard's membership.
    """
    CHART_TYPES = [
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('scatter', 'Scatter Plot'),
        ('table', 'Table'),
    ]
    
    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name='charts',
    )
    name = models.CharField(max_length=255)
    chart_type = models.CharField(max_length=50, choices=CHART_TYPES, default='bar')
    query = models.TextField(blank=True, default='')
    config = models.JSONField(default=dict, blank=True)
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_charts',
    )
    
    class Meta:
        ordering = ['position', '-created_at']
    
    def __str__(self) -> str:
        return f"{self.name} ({self.dashboard.name})"
    
    class GuitarMeta:
        fields = [
            'id', 'dashboard_id', 'name', 'chart_type', 'query', 'config',
            'position', 'created_at', 'updated_at', 'created_by_id',
        ]
        writable_fields = ['dashboard_id', 'name', 'chart_type', 'query', 'config', 'position']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by_id']
        filterable_fields = ['dashboard_id', 'chart_type', 'created_by_id']
        orderable_fields = ['position', 'created_at', 'name']
    
    class GuitarManager:
        chain_permissions = True
        
        def filter_read(self, request, queryset):
            """Can see charts in dashboards you're a member of."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(dashboard__members=request.user).distinct()
        
        def filter_write(self, request, queryset):
            """Creators and editors can update charts."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                dashboard__dashboardmembership__user=request.user,
                dashboard__dashboardmembership__role__in=['creator', 'editor'],
            ).distinct()
        
        def filter_delete(self, request, queryset):
            """Creators and editors can delete charts."""
            # Same as write - editors CAN delete charts (just not dashboards)
            return self.filter_write(request, queryset)
        
        def check_create(self, request, data):
            """Creators and editors can add charts to dashboards."""
            dashboard_id = data.get('dashboard_id')
            
            membership = DashboardMembership.objects.filter(
                user=request.user,
                dashboard_id=dashboard_id,
                role__in=['creator', 'editor'],
            ).first()
            
            if not membership:
                raise PermissionDenied("Must be creator or editor to add charts")
            
            data['created_by_id'] = request.user.id
            return data
