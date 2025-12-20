"""
Comprehensive tests for the Dashboard app demonstrating
Django Guitar's Model-Level Security (MLS) patterns.

These tests cover:
1. Role-based access (creator/editor/viewer)
2. Cascading permissions (charts via dashboard)
3. Permission chaining (write chains from read)
4. check_create validation
5. Lifecycle hooks (post_create)
"""

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User

from guitar.tests import GuitarTestMixin
from example_project.dashboard.models import Dashboard, DashboardMembership, Chart


class DashboardPermissionTests(GuitarTestMixin, TestCase):
    """Tests for Dashboard model permissions."""
    
    def setUp(self):
        """Set up test users and data."""
        self.creator = User.objects.create_user('creator', 'creator@test.com', 'pass')
        self.editor = User.objects.create_user('editor', 'editor@test.com', 'pass')
        self.viewer = User.objects.create_user('viewer', 'viewer@test.com', 'pass')
        self.outsider = User.objects.create_user('outsider', 'outsider@test.com', 'pass')
        
        # Create a dashboard with the creator
        self.dashboard = Dashboard.objects.create(
            name='Test Dashboard',
            description='A test dashboard',
        )
        
        # Add memberships
        DashboardMembership.objects.create(
            user=self.creator,
            dashboard=self.dashboard,
            role='creator',
        )
        DashboardMembership.objects.create(
            user=self.editor,
            dashboard=self.dashboard,
            role='editor',
        )
        DashboardMembership.objects.create(
            user=self.viewer,
            dashboard=self.dashboard,
            role='viewer',
        )
    
    # === READ TESTS ===
    
    def test_creator_can_read_dashboard(self):
        """Creator can see their dashboard."""
        self.client.force_login(self.creator)
        response = self.guitar_get(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Test Dashboard')
    
    def test_editor_can_read_dashboard(self):
        """Editor can see the dashboard."""
        self.client.force_login(self.editor)
        response = self.guitar_get(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 200)
    
    def test_viewer_can_read_dashboard(self):
        """Viewer can see the dashboard."""
        self.client.force_login(self.viewer)
        response = self.guitar_get(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 200)
    
    def test_outsider_cannot_read_dashboard(self):
        """Outsider cannot see the dashboard (filtered out)."""
        self.client.force_login(self.outsider)
        response = self.guitar_get(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 404)
    
    def test_unauthenticated_cannot_read_dashboard(self):
        """Unauthenticated user cannot access dashboards."""
        response = self.guitar_get(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 403)
    
    def test_list_only_shows_member_dashboards(self):
        """List only shows dashboards user is a member of."""
        # Create another dashboard that outsider owns
        other_dashboard = Dashboard.objects.create(name='Other Dashboard')
        DashboardMembership.objects.create(
            user=self.outsider,
            dashboard=other_dashboard,
            role='creator',
        )
        
        # Viewer should only see the first dashboard
        self.client.force_login(self.viewer)
        response = self.guitar_get(Dashboard)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.dashboard.id)
    
    # === UPDATE TESTS ===
    
    def test_creator_can_update_dashboard(self):
        """Creator can update the dashboard."""
        self.client.force_login(self.creator)
        response = self.guitar_patch(Dashboard, self.dashboard.id, {'name': 'Updated Name'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Updated Name')
    
    def test_editor_can_update_dashboard(self):
        """Editor can update the dashboard."""
        self.client.force_login(self.editor)
        response = self.guitar_patch(Dashboard, self.dashboard.id, {'name': 'Editor Update'})
        self.assertEqual(response.status_code, 200)
    
    def test_viewer_cannot_update_dashboard(self):
        """Viewer cannot update the dashboard."""
        self.client.force_login(self.viewer)
        response = self.guitar_patch(Dashboard, self.dashboard.id, {'name': 'Viewer Update'})
        self.assertEqual(response.status_code, 404)  # Filtered out
    
    def test_outsider_cannot_update_dashboard(self):
        """Outsider cannot update the dashboard."""
        self.client.force_login(self.outsider)
        response = self.guitar_patch(Dashboard, self.dashboard.id, {'name': 'Outsider Update'})
        self.assertEqual(response.status_code, 404)
    
    # === DELETE TESTS ===
    
    def test_creator_can_delete_dashboard(self):
        """Creator can delete the dashboard."""
        self.client.force_login(self.creator)
        response = self.guitar_delete(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Dashboard.objects.filter(id=self.dashboard.id).exists())
    
    def test_editor_cannot_delete_dashboard(self):
        """Editor cannot delete the dashboard."""
        self.client.force_login(self.editor)
        response = self.guitar_delete(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 404)  # Filtered out
        self.assertTrue(Dashboard.objects.filter(id=self.dashboard.id).exists())
    
    def test_viewer_cannot_delete_dashboard(self):
        """Viewer cannot delete the dashboard."""
        self.client.force_login(self.viewer)
        response = self.guitar_delete(Dashboard, self.dashboard.id)
        self.assertEqual(response.status_code, 404)
    
    # === CREATE TESTS ===
    
    def test_authenticated_user_can_create_dashboard(self):
        """Any authenticated user can create a dashboard."""
        self.client.force_login(self.outsider)
        response = self.guitar_post(Dashboard, {
            'name': 'New Dashboard',
            'description': 'Created by outsider',
        })
        self.assertEqual(response.status_code, 200)
        
        # Check that creator was auto-added as a member
        new_dashboard = Dashboard.objects.get(name='New Dashboard')
        membership = DashboardMembership.objects.get(
            user=self.outsider,
            dashboard=new_dashboard,
        )
        self.assertEqual(membership.role, 'creator')


class DashboardMembershipPermissionTests(GuitarTestMixin, TestCase):
    """Tests for DashboardMembership model permissions."""
    
    def setUp(self):
        """Set up test users and data."""
        self.creator = User.objects.create_user('creator', 'creator@test.com', 'pass')
        self.editor = User.objects.create_user('editor', 'editor@test.com', 'pass')
        self.viewer = User.objects.create_user('viewer', 'viewer@test.com', 'pass')
        self.new_user = User.objects.create_user('newuser', 'newuser@test.com', 'pass')
        
        self.dashboard = Dashboard.objects.create(name='Test Dashboard')
        
        self.creator_membership = DashboardMembership.objects.create(
            user=self.creator,
            dashboard=self.dashboard,
            role='creator',
        )
        self.editor_membership = DashboardMembership.objects.create(
            user=self.editor,
            dashboard=self.dashboard,
            role='editor',
        )
        self.viewer_membership = DashboardMembership.objects.create(
            user=self.viewer,
            dashboard=self.dashboard,
            role='viewer',
        )
    
    # === READ TESTS ===
    
    def test_member_can_see_all_memberships(self):
        """Members can see all memberships for their dashboards."""
        self.client.force_login(self.viewer)
        response = self.guitar_get(DashboardMembership, dashboard_id=self.dashboard.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)
    
    def test_outsider_cannot_see_memberships(self):
        """Non-members cannot see memberships."""
        self.client.force_login(self.new_user)
        response = self.guitar_get(DashboardMembership, dashboard_id=self.dashboard.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
    
    # === CREATE TESTS (INVITE) ===
    
    def test_creator_can_invite_member(self):
        """Creator can invite new members."""
        self.client.force_login(self.creator)
        response = self.guitar_post(DashboardMembership, {
            'user_id': self.new_user.id,
            'dashboard_id': self.dashboard.id,
            'role': 'viewer',
        })
        self.assertEqual(response.status_code, 200)
        
        membership = DashboardMembership.objects.get(user=self.new_user)
        self.assertEqual(membership.role, 'viewer')
        self.assertEqual(membership.invited_by_id, self.creator.id)
    
    def test_editor_cannot_invite_member(self):
        """Editor cannot invite new members."""
        self.client.force_login(self.editor)
        response = self.guitar_post(DashboardMembership, {
            'user_id': self.new_user.id,
            'dashboard_id': self.dashboard.id,
            'role': 'viewer',
        })
        self.assertEqual(response.status_code, 403)
    
    def test_viewer_cannot_invite_member(self):
        """Viewer cannot invite new members."""
        self.client.force_login(self.viewer)
        response = self.guitar_post(DashboardMembership, {
            'user_id': self.new_user.id,
            'dashboard_id': self.dashboard.id,
            'role': 'viewer',
        })
        self.assertEqual(response.status_code, 403)
    
    # === DELETE TESTS (REMOVE MEMBER) ===
    
    def test_creator_can_remove_editor(self):
        """Creator can remove an editor."""
        self.client.force_login(self.creator)
        response = self.guitar_delete(DashboardMembership, self.editor_membership.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            DashboardMembership.objects.filter(id=self.editor_membership.id).exists()
        )
    
    def test_creator_can_remove_viewer(self):
        """Creator can remove a viewer."""
        self.client.force_login(self.creator)
        response = self.guitar_delete(DashboardMembership, self.viewer_membership.id)
        self.assertEqual(response.status_code, 200)
    
    def test_creator_cannot_remove_self(self):
        """Creator cannot remove themselves (last creator protection)."""
        self.client.force_login(self.creator)
        response = self.guitar_delete(DashboardMembership, self.creator_membership.id)
        self.assertEqual(response.status_code, 404)  # Filtered out
        self.assertTrue(
            DashboardMembership.objects.filter(id=self.creator_membership.id).exists()
        )
    
    def test_editor_cannot_remove_members(self):
        """Editor cannot remove any members."""
        self.client.force_login(self.editor)
        response = self.guitar_delete(DashboardMembership, self.viewer_membership.id)
        self.assertEqual(response.status_code, 404)


class ChartPermissionTests(GuitarTestMixin, TestCase):
    """Tests for Chart model permissions (cascading from Dashboard)."""
    
    def setUp(self):
        """Set up test users and data."""
        self.creator = User.objects.create_user('creator', 'creator@test.com', 'pass')
        self.editor = User.objects.create_user('editor', 'editor@test.com', 'pass')
        self.viewer = User.objects.create_user('viewer', 'viewer@test.com', 'pass')
        self.outsider = User.objects.create_user('outsider', 'outsider@test.com', 'pass')
        
        self.dashboard = Dashboard.objects.create(name='Test Dashboard')
        
        DashboardMembership.objects.create(
            user=self.creator, dashboard=self.dashboard, role='creator',
        )
        DashboardMembership.objects.create(
            user=self.editor, dashboard=self.dashboard, role='editor',
        )
        DashboardMembership.objects.create(
            user=self.viewer, dashboard=self.dashboard, role='viewer',
        )
        
        self.chart = Chart.objects.create(
            dashboard=self.dashboard,
            name='Test Chart',
            chart_type='bar',
            created_by=self.creator,
        )
    
    # === READ TESTS ===
    
    def test_creator_can_read_charts(self):
        """Creator can see charts in their dashboard."""
        self.client.force_login(self.creator)
        response = self.guitar_get(Chart, self.chart.id)
        self.assertEqual(response.status_code, 200)
    
    def test_editor_can_read_charts(self):
        """Editor can see charts."""
        self.client.force_login(self.editor)
        response = self.guitar_get(Chart, self.chart.id)
        self.assertEqual(response.status_code, 200)
    
    def test_viewer_can_read_charts(self):
        """Viewer can see charts."""
        self.client.force_login(self.viewer)
        response = self.guitar_get(Chart, self.chart.id)
        self.assertEqual(response.status_code, 200)
    
    def test_outsider_cannot_read_charts(self):
        """Outsider cannot see charts (no dashboard access)."""
        self.client.force_login(self.outsider)
        response = self.guitar_get(Chart, self.chart.id)
        self.assertEqual(response.status_code, 404)
    
    # === CREATE TESTS ===
    
    def test_creator_can_create_chart(self):
        """Creator can add charts."""
        self.client.force_login(self.creator)
        response = self.guitar_post(Chart, {
            'dashboard_id': self.dashboard.id,
            'name': 'New Chart',
            'chart_type': 'line',
        })
        self.assertEqual(response.status_code, 200)
        
        # Check created_by was set
        new_chart = Chart.objects.get(name='New Chart')
        self.assertEqual(new_chart.created_by_id, self.creator.id)
    
    def test_editor_can_create_chart(self):
        """Editor can add charts."""
        self.client.force_login(self.editor)
        response = self.guitar_post(Chart, {
            'dashboard_id': self.dashboard.id,
            'name': 'Editor Chart',
            'chart_type': 'pie',
        })
        self.assertEqual(response.status_code, 200)
    
    def test_viewer_cannot_create_chart(self):
        """Viewer cannot add charts."""
        self.client.force_login(self.viewer)
        response = self.guitar_post(Chart, {
            'dashboard_id': self.dashboard.id,
            'name': 'Viewer Chart',
            'chart_type': 'bar',
        })
        self.assertEqual(response.status_code, 403)
    
    def test_outsider_cannot_create_chart(self):
        """Outsider cannot add charts to dashboard they don't have access to."""
        self.client.force_login(self.outsider)
        response = self.guitar_post(Chart, {
            'dashboard_id': self.dashboard.id,
            'name': 'Outsider Chart',
            'chart_type': 'bar',
        })
        self.assertEqual(response.status_code, 403)
    
    # === UPDATE TESTS ===
    
    def test_creator_can_update_chart(self):
        """Creator can update charts."""
        self.client.force_login(self.creator)
        response = self.guitar_patch(Chart, self.chart.id, {'name': 'Updated Chart'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Updated Chart')
    
    def test_editor_can_update_chart(self):
        """Editor can update charts."""
        self.client.force_login(self.editor)
        response = self.guitar_patch(Chart, self.chart.id, {'name': 'Editor Updated'})
        self.assertEqual(response.status_code, 200)
    
    def test_viewer_cannot_update_chart(self):
        """Viewer cannot update charts."""
        self.client.force_login(self.viewer)
        response = self.guitar_patch(Chart, self.chart.id, {'name': 'Viewer Updated'})
        self.assertEqual(response.status_code, 404)
    
    # === DELETE TESTS ===
    
    def test_creator_can_delete_chart(self):
        """Creator can delete charts."""
        self.client.force_login(self.creator)
        response = self.guitar_delete(Chart, self.chart.id)
        self.assertEqual(response.status_code, 200)
    
    def test_editor_can_delete_chart(self):
        """Editor can delete charts (different from dashboard delete)."""
        self.client.force_login(self.editor)
        response = self.guitar_delete(Chart, self.chart.id)
        self.assertEqual(response.status_code, 200)
    
    def test_viewer_cannot_delete_chart(self):
        """Viewer cannot delete charts."""
        self.client.force_login(self.viewer)
        response = self.guitar_delete(Chart, self.chart.id)
        self.assertEqual(response.status_code, 404)


class QueryFeatureTests(GuitarTestMixin, TestCase):
    """Tests for query features: filtering, ordering, pagination."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        
        self.dashboard = Dashboard.objects.create(name='Test Dashboard')
        DashboardMembership.objects.create(
            user=self.user, dashboard=self.dashboard, role='creator',
        )
        
        # Create multiple charts
        for i in range(5):
            Chart.objects.create(
                dashboard=self.dashboard,
                name=f'Chart {i}',
                chart_type='bar' if i % 2 == 0 else 'line',
                position=i,
                created_by=self.user,
            )
    
    def test_filter_by_field(self):
        """Filter by exact field match."""
        self.client.force_login(self.user)
        response = self.guitar_get(Chart, chart_type='bar')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)  # Charts 0, 2, 4
        for chart in data:
            self.assertEqual(chart['chart_type'], 'bar')
    
    def test_filter_by_dashboard(self):
        """Filter charts by dashboard."""
        self.client.force_login(self.user)
        response = self.guitar_get(Chart, dashboard_id=self.dashboard.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)
    
    def test_ordering(self):
        """Test ordering by field."""
        self.client.force_login(self.user)
        response = self.guitar_get(Chart, _order='-position')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        positions = [c['position'] for c in data]
        self.assertEqual(positions, sorted(positions, reverse=True))
    
    def test_pagination_limit(self):
        """Test limit parameter."""
        self.client.force_login(self.user)
        response = self.guitar_get(Chart, _limit=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
    
    def test_pagination_offset(self):
        """Test offset parameter."""
        self.client.force_login(self.user)
        
        # Get all charts
        response_all = self.guitar_get(Chart, _order='position')
        all_charts = response_all.json()
        
        # Get charts with offset
        response_offset = self.guitar_get(Chart, _order='position', _offset=2)
        offset_charts = response_offset.json()
        
        self.assertEqual(len(offset_charts), 3)
        self.assertEqual(offset_charts[0]['id'], all_charts[2]['id'])
    
    def test_limit_and_offset(self):
        """Test limit and offset together."""
        self.client.force_login(self.user)
        response = self.guitar_get(Chart, _order='position', _limit=2, _offset=1)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Chart 1')
        self.assertEqual(data[1]['name'], 'Chart 2')


class TypeScriptGenerationTests(TestCase):
    """Tests for TypeScript client generation."""
    
    def test_generate_guitar_client_command(self):
        """Test the generate_guitar_client management command runs without error."""
        import tempfile
        import os
        from django.core.management import call_command
        from io import StringIO
        
        with tempfile.TemporaryDirectory() as tmpdir:
            out = StringIO()
            call_command(
                'generate_guitar_client',
                output=tmpdir,
                stdout=out,
            )
            
            output = out.getvalue()
            self.assertIn('Generated TypeScript client', output)
            
            # Check files were created
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'index.ts')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'client.ts')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'types.ts')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'models', 'Dashboard.ts')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'models', 'Chart.ts')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'models', 'DashboardMembership.ts')))
