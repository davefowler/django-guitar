"""
Test mixins for Guitar models.
"""

from typing import Any, Dict, Optional, Type
import json
from django.test import TestCase, Client
from django.db import models


class GuitarTestMixin:
    """
    Mixin that provides helper methods for testing Guitar models.
    
    Usage:
        class ChartPermissionTests(GuitarTestMixin, TestCase):
            def test_owner_can_read(self):
                self.client.force_login(self.user)
                response = self.guitar_get(Chart, self.chart.id)
                self.assertEqual(response.status_code, 200)
    """
    
    guitar_base_url: str = '/guitar'
    
    def guitar_get(
        self,
        model_class: Type[models.Model],
        pk: Optional[int] = None,
        **query_params,
    ):
        """
        GET a single object or list of objects.
        
        Args:
            model_class: The Guitar model class
            pk: Optional primary key for single object retrieval
            **query_params: Query parameters for filtering
        """
        endpoint = model_class._get_endpoint_name()
        
        if pk is not None:
            url = f'{self.guitar_base_url}/{endpoint}/{pk}/'
        else:
            url = f'{self.guitar_base_url}/{endpoint}/'
        
        if query_params:
            params = '&'.join(f'{k}={v}' for k, v in query_params.items())
            url = f'{url}?{params}'
        
        return self.client.get(url)
    
    def guitar_post(
        self,
        model_class: Type[models.Model],
        data: Dict[str, Any],
    ):
        """
        POST to create a new object.
        
        Args:
            model_class: The Guitar model class
            data: The data to create the object with
        """
        endpoint = model_class._get_endpoint_name()
        url = f'{self.guitar_base_url}/{endpoint}/'
        
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
        )
    
    def guitar_patch(
        self,
        model_class: Type[models.Model],
        pk: int,
        data: Dict[str, Any],
    ):
        """
        PATCH to update an existing object.
        
        Args:
            model_class: The Guitar model class
            pk: Primary key of the object to update
            data: The data to update the object with
        """
        endpoint = model_class._get_endpoint_name()
        url = f'{self.guitar_base_url}/{endpoint}/{pk}/'
        
        return self.client.patch(
            url,
            data=json.dumps(data),
            content_type='application/json',
        )
    
    def guitar_delete(
        self,
        model_class: Type[models.Model],
        pk: int,
    ):
        """
        DELETE an object.
        
        Args:
            model_class: The Guitar model class
            pk: Primary key of the object to delete
        """
        endpoint = model_class._get_endpoint_name()
        url = f'{self.guitar_base_url}/{endpoint}/{pk}/'
        
        return self.client.delete(url)
    
    def assertGuitarResponse(
        self,
        response,
        status_code: int = 200,
        contains: Optional[Dict[str, Any]] = None,
    ):
        """
        Assert the response status and optionally check response data.
        
        Args:
            response: The response object
            status_code: Expected status code
            contains: Optional dict of key-value pairs that should be in the response
        """
        self.assertEqual(response.status_code, status_code)
        
        if contains and status_code < 400:
            data = response.json()
            for key, value in contains.items():
                self.assertIn(key, data)
                self.assertEqual(data[key], value)
    
    def assertGuitarCount(
        self,
        model_class: Type[models.Model],
        count: int,
        **query_params,
    ):
        """
        Assert the count of objects returned from a Guitar query.
        
        Args:
            model_class: The Guitar model class
            count: Expected count
            **query_params: Query parameters for filtering
        """
        response = self.guitar_get(model_class, **query_params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), count)
