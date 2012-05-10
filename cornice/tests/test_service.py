# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest

from cornice import Service
from cornice.tests import validationapp

_validator = lambda req: True
_validator2 = lambda req: True


class TestService(unittest.TestCase):

    def test_service_instanciation(self):
        service = Service("coconuts", "/migrate")
        self.assertEquals(service.name, "coconuts")
        self.assertEquals(service.path, "/migrate")
        self.assertEquals(service.renderer, Service.renderer)

        service = Service("coconuts", "/migrate", renderer="html")
        self.assertEquals(service.renderer, "html")

        # test that lists are also set
        validators = [lambda x: True, ]
        service = Service("coconuts", "/migrate", validators=validators)
        self.assertEquals(service.validators, validators)

    def test_get_arguments(self):
        service = Service("coconuts", "/migrate")
        # not specifying anything, we should get the default values
        args = service.get_arguments({})
        for arg in Service.mandatory_arguments:
            self.assertEquals(args[arg], getattr(Service, arg, None))

        # calling this method on a configured service should use the values
        # passed at instanciation time as default values
        service = Service("coconuts", "/migrate", renderer="html")
        args = service.get_arguments({})
        self.assertEquals(args['renderer'], 'html')

        # if we specify another renderer for this service, despite the fact
        # that one is already set in the instance, this one should be used
        args = service.get_arguments({'renderer': 'foobar'})
        self.assertEquals(args['renderer'], 'foobar')

        # test that list elements are not overwritten
        # define a validator for the needs of the test

        service = Service("vaches", "/fetchez", validators=(_validator,))
        self.assertEquals(len(service.validators), 1)
        args = service.get_arguments({'validators': (_validator2,)})

        # the list of validators didn't changed
        self.assertEquals(len(service.validators), 1)

        # but the one returned contains 2 validators
        self.assertEquals(len(args['validators']), 2)

        # test that exclude effectively removes the items from the list of
        # validators / filters it returns, without removing it from the ones
        # registered for the service.
        service = Service("open bar", "/bar", validators=(_validator,
                                                          _validator2))
        self.assertEquals(service.validators, [_validator, _validator2])

        args = service.get_arguments({"exclude": _validator2})
        self.assertEquals(args['validators'], [_validator])

        # defining some non-mandatory arguments in a service should make
        # them available on further calls to get_arguments.

        service = Service("vaches", "/fetchez", foobar="baz")
        self.assertIn("foobar", service.arguments)
        self.assertIn("foobar", service.get_arguments())

    def test_view_registration(self):
        # registering a new view should make it available in the list.
        # The methods list is populated
        service = Service("color", "/favorite-color")

        def view(request):
            pass
        service.hook_view("post", view, validators=(_validator,))
        self.assertEquals(len(service.definitions), 1)
        method, _view, _ = service.definitions[0]

        # the view had been registered. we also test here that the method had
        # been inserted capitalized (POST instead of post)
        self.assertEquals(("POST", view), (method, _view))

    def test_decorators(self):
        service = Service("color", "/favorite-color")

        @service.get()
        def get_favorite_color(request):
            return "blue, hmm, red, hmm, aaaaaaaah"

        method, view, _ = service.definitions[0]
        self.assertEquals(("GET", get_favorite_color), (method, view))

        @service.post(accept='text/plain', renderer='plain')
        @service.post(accept='application/json')
        def post_favorite_color(request):
            pass

        # using multiple decorators on a resource should register them all in
        # as many different definitions in the service
        self.assertEquals(3, len(service.definitions))

    def test_get_acceptable(self):
        # defining a service with different "accept" headers, we should be able
        # to retrieve this information easily
        service = Service("color", "/favorite-color")
        service.hook_view("GET", lambda x: "blue", accept="text/plain")
        self.assertEquals(service.get_acceptable("GET"), ['text/plain'])

        service.hook_view("GET", lambda x: "blue", accept="application/json")
        self.assertEquals(service.get_acceptable("GET"),
                          ['text/plain', 'application/json'])

        # adding a view for the POST method should not break everything :-)
        service.hook_view("POST", lambda x: "ok", accept=('foo/bar'))
        self.assertEquals(service.get_acceptable("GET"),
                          ['text/plain', 'application/json'])
        # and of course the list of accepted content-types  should be available
        # for the "POST" as well.
        self.assertEquals(service.get_acceptable("POST"),
                          ['foo/bar'])

        # it is possible to give acceptable content-types dynamically at
        # run-time. You don't always want to have the callables when retrieving
        # all the acceptable content-types
        service.hook_view("POST", lambda x: "ok", accept=lambda r: "text/json")
        self.assertEquals(len(service.get_acceptable("POST")), 2)
        self.assertEquals(len(service.get_acceptable("POST", True)), 1)

    if validationapp.COLANDER:
        def test_schemas_for(self):
            schema = validationapp.FooBarSchema
            service = Service("color", "/favorite-color")
            service.hook_view("GET", lambda x: "red", schema=schema)
            self.assertEquals(len(service.schemas_for("GET")), 1)
            service.hook_view("GET", lambda x: "red", validators=_validator,
                              schema=schema)
            self.assertEquals(len(service.schemas_for("GET")), 2)

    def test_class_parameters(self):
        # when passing a "klass" argument, it gets registered. It also tests
        # that the view argument can be a string and not a callable.
        class TemperatureCooler(object):
            def get_fresh_air(self):
                pass
        service = Service("TemperatureCooler", "/freshair",
                          klass=TemperatureCooler)
        service.hook_view("get", "get_fresh_air")

        self.assertEquals(len(service.definitions), 1)

        method, view, args = service.definitions[0]
        self.assertEquals(view, "get_fresh_air")
        self.assertEquals(args["klass"], TemperatureCooler)