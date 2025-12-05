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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
import copy
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    def assertProductEquals(self, product1, product2):
        """asserts that product1 has the same properties than product2"""
        self.assertEqual(product1.id, product2.id)
        self.assertEqual(product1.name, product2.name)
        self.assertEqual(product1.description, product2.description)
        self.assertEqual(product1.available, product2.available)
        self.assertEqual(product1.price, product2.price)
        self.assertEqual(product1.category, product2.category)

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_product(self):
        """tests that a previously created product can be read from the db"""
        products = Product.all()
        self.assertEqual(products, [])

        product = ProductFactory()
        product.id = None
        app.logger.info("Creating product: " + str(product))
        product.create()
        self.assertIsNotNone(product.id)

        products = Product.all()
        db_product = products[0]
        app.logger.info("Fetched product: " + str(db_product))

        self.assertProductEquals(product, db_product)

    def test_update_product(self):
        """tests that a product can be updated in the db"""
        products = Product.all()
        self.assertEqual(products, [])

        product = ProductFactory()
        product.id = None
        app.logger.info("Creating product: " + str(product))
        product.create()
        products = Product.all()
        product = products[0]

        id_before = product.id
        new_description = product.description + " new"
        product.description = new_description
        app.logger.info("Updating product: " + str(product))
        product.update()
        self.assertEqual(product.id, id_before)
        self.assertEqual(product.description, new_description)

        products = Product.all()
        self.assertEqual(len(products), 1)
        db_product = products[0]
        app.logger.info("Fetched product: " + str(db_product))

        self.assertProductEquals(product, db_product)

    def test_update_product_with_empty_id(self):
        """tests that an error is raised, when updating a procduct without id"""
        product = ProductFactory()
        product.id = None
        app.logger.info("Creating product: " + str(product))
        product.create()

        product.id = None
        app.logger.info("Updating product: " + str(product))
        self.assertRaises(DataValidationError, product.update) 

    def test_delete_product(self):
        """tests that a product can be deleted from the db"""
        products = Product.all()
        self.assertEqual(products, [])

        product = ProductFactory()
        product.id = None
        product.create()
        products = Product.all()
        self.assertEqual(len(products), 1)
        product.delete()
        products = Product.all()
        self.assertEqual(len(products), 0)

    def test_list_all_product(self):
        """tests that all products from the db can be listed"""
        products = Product.all()
        self.assertEqual(products, [])

        created_products = []
        for idx in range(5):
            product = ProductFactory()
            product.id = None
            product.create()
            created_products.append(product)

            products = Product.all()
            self.assertEqual(len(products), idx+1)
            self.assertIn(product, products)

        for created_product in created_products:
            self.assertIn(created_product, products)


    def test_search_product_by_name(self):
        """tests that a product can be found in the db by searching for its name"""
        product = ProductFactory()
        product.id = None
        product.create()

        db_products = Product.find_by_name(product.name)
        self.assertIn(product, db_products)

    def test_search_product_by_category(self):
        """tests that a product can be found in the db by searching for its category"""
        product = ProductFactory()
        product.id = None
        product.create()

        db_products = Product.find_by_category(product.category)
        self.assertIn(product, db_products)

    def test_search_product_by_availability(self):
        """tests that a product can be found in the db by searching for availability"""
        product = ProductFactory()
        product.id = None
        product.create()

        db_products = Product.find_by_availability(product.available)
        self.assertIn(product, db_products)