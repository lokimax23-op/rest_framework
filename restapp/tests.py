from rest_framework import status
from rest_framework.test import APITestCase

class CategoryApiTests(APITestCase):
    def test_home_route_returns_portal_html(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'HiiT Learning Hub')

    def test_api_root_returns_project_info(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['project'],
            'HiiT Student Course Management & Resource Portal',
        )

    def test_get_categories_returns_empty_list_initially(self):
        response = self.client.get('/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_create_category_returns_created_category(self):
        response = self.client.post('/categories/', {'name': 'Breakfast'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Breakfast')

    def test_create_category_rejects_missing_name(self):
        response = self.client.post('/categories/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
