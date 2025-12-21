######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch
from flask import abort
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product, Category
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_non_existing_route(self):
        """It should return an 404 error on nonexisting route"""
        response = self.client.get("/not-existing")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_existing_method(self):
        """It should return an 405 error on nonexisting method for a route"""
        response = self.client.delete(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch('service.routes.check_content_type')
    def test_internal_server_error(self, mock_func):
        """It should return an HTTP 500 error on internal error"""
        mock_func.side_effect = lambda type: abort(500, "Mocked Internal Error Text")
        response = self.client.post(BASE_URL, data={})

        self.assertEqual(response.status_code, 500)

    # ----------------------------------------------------------
    # TEST READ
    # ----------------------------------------------------------
    def test_read_product(self):
        """It should read an existing product from the db"""
        test_product = (self._create_products())[0]
        product_url = BASE_URL + '/' + str(test_product.id)
        response = self.client.get(product_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check the data is correct
        db_product = response.get_json()
        self.assertEqual(db_product["name"], test_product.name)
        self.assertEqual(db_product["description"], test_product.description)
        self.assertEqual(Decimal(db_product["price"]), test_product.price)
        self.assertEqual(db_product["available"], test_product.available)
        self.assertEqual(db_product["category"], test_product.category.name)

    def test_read_nonexisting_product(self):
        """It should throw an error when trying to read a nonexisting product"""
        product_url = BASE_URL + '/0'
        response = self.client.get(product_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST UPDATE
    # ----------------------------------------------------------
    def test_update_product(self):
        """It should update an existing product in the db"""
        test_product = (self._create_products())[0]
        product_url = BASE_URL + '/' + str(test_product.id)

        new_name = test_product.name + '_test'
        data = test_product.serialize()
        data["name"] = new_name

        response = self.client.put(product_url, json=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_data = response.get_json()
        self.assertEqual(updated_data["name"], new_name)

        response = self.client.get(product_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_product = response.get_json()
        self.assertEqual(updated_product["name"], new_name)

    def test_update_nonexisting_product(self):
        """It should give an 404 when trying to update an non-existing product"""
        test_product = (self._create_products())[0]
        product_url = BASE_URL + '/0'

        data = test_product.serialize()

        response = self.client.put(product_url, json=data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_invalid_data(self):
        """It should give an 400 when trying to update with invalid data"""
        test_product = (self._create_products())[0]
        product_url = BASE_URL + '/' + str(test_product.id)

        invalid_data = test_product.serialize()
        invalid_data["available"] = 'wrong type'
        response = self.client.put(product_url, json=invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ----------------------------------------------------------
    # TEST DELETE
    # ----------------------------------------------------------
    def test_delete_product(self):
        """It should delete an existing product from the db"""
        test_product = (self._create_products())[0]
        product_url = BASE_URL + '/' + str(test_product.id)

        response = self.client.delete(product_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(product_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_delete_non_existing_product(self):
        """It should throw an error, when trying to delete a non-existing product from the db"""
        product_url = BASE_URL + '/0'

        response = self.client.delete(product_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST LIST ALL
    # ----------------------------------------------------------
    def test_list_all_products(self):
        """It should list all products in the database, on get request on the base url"""
        product_count = 10
        self._create_products(product_count)

        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), product_count)

    def test_list_all_products_empty_db(self):
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 0)

    # ----------------------------------------------------------
    # TEST LIST BY NAME
    # ----------------------------------------------------------
    def test_list_by_name(self):
        """It should list all products in the database, that have a specific name"""
        total_products = 10
        named_products = 4
        test_name = "specific name"

        products = self._create_products(total_products)
        for idx in range(named_products):
            product = products[idx]
            product.name = test_name
            product_data = product.serialize()
            product_url = BASE_URL + "/" + str(product.id)
            self.client.put(product_url, json=product_data)

        url = BASE_URL + "?name=" + quote_plus(test_name)
        response = self.client.get(url)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), named_products)
        
    def test_list_by_name_nothing_found(self):
        total_products = 10
        test_name = "nonexisting product name"

        products = self._create_products(total_products)
        url = BASE_URL + "?name=" + quote_plus(test_name)
        response = self.client.get(url)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 0)

    # ----------------------------------------------------------
    # TEST LIST BY CATEGORY
    # ----------------------------------------------------------
    def test_list_by_category(self):
        """It should list all products in the database, that have a specific category"""
        total_products = 50

        products = self._create_products(total_products)
        food_products = [p for p in products if p.category == Category.FOOD]

        url = BASE_URL + "?category=" + str(Category.FOOD.value)
        response = self.client.get(url)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), len(food_products))
        
    def test_list_by_category_nothing_found(self):
        url = BASE_URL + "?category=" + str(Category.FOOD.value)
        response = self.client.get(url)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 0)

    # ----------------------------------------------------------
    # TEST LIST BY AVAILABILITY
    # ----------------------------------------------------------
    def test_list_by_availablility(self):
        """It should list all products in the database, that have a specific availability"""
        total_products = 20

        products = self._create_products(total_products)
        available_products = [p for p in products if p.available == True]

        url = BASE_URL + "?available=" + str(True)
        response = self.client.get(url)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), len(available_products))
        
    def test_list_by_available_nothing_found(self):
        url = BASE_URL + "?available=" + str(False)
        response = self.client.get(url)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 0)

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        logging.debug("data = %s", data)
        return len(data)
