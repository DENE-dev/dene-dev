'''
MIT License

Copyright (c) 2021 Caio Alexandre

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from collections import defaultdict
from typing import List, Callable, Dict, Optional

from .errors import InvalidPath, RouteAlreadyExists, InvalidHTTPMethod


HTTP_METHODS = (
    'GET', 'HEAD',
    'POST', 'PUT',
    'DELETE', 'CONNECT',
    'OPTIONS', 'TRACE',
    'PATCH'
)


class Router:
    """Represents a router for adding dynamic routes.

    Examples
    --------

    Adding a simple route dynamically: ::

        router = kastle.Router()

        @router.get('/about')
        async def about():
            # This function will be called whenever
            # the /about route is requested.
            pass

        # Append this route to the application index endpoint.
        app.add_router('/', router)

    """

    __slots__ = ('_routes',)

    def __init__(self) -> None:
        self._routes = {}

    def route(
        self,
        path: str,
        *,
        methods: Optional[List[str]] = None
    ) -> None:
        """Creates a route to the router.

        Parameters
        ----------
        path: :class:`str`
            The path to the endpoint. It should always start with
            ``/``.
        methods: List[:class:`str`]
            The HTTP methods this route should listen to. Defaults to
            ``['GET']``.

        Raises
        ------
        :class:`ValueError`
            If the methods parameter is an empty list.
        :class:`InvalidPath`
            If endpoint path is invalid.
        :class:`InvalidHTTPMethod`
            If any of the HTTP methods given is invalid.
        :class:`RouteAlreadyExists`
            If a route to the endpoint path already exists.
        """
        if methods is None:
            methods = ['GET']

        if not len(methods):
            raise ValueError('methods must have at least one HTTP method')

        def decorator(func: Callable[[], None]):
            if not path.startswith('/'):
                raise InvalidPath("paths must start with '/'")

            if path not in self._routes:
                self._routes[path] = defaultdict(None)

            for method in methods:
                routes = self._routes[path]
                method = method.upper()

                if method not in HTTP_METHODS:
                    raise InvalidHTTPMethod(method)

                if method in routes:
                    raise RouteAlreadyExists(method, path)

                self._routes[path][method] = func

        return decorator

    def get(self, path: str) -> None:
        """Create a route of type ``GET`` to the router.

        This is a shortcut to ``Router.route(path, methods=['GET'])``.

        Parameters
        ----------
        path: :class:`str`
            The path to the endpoint. It should always start with
            ``/``.

        Raises
        ------
        :class:`InvalidPath`
            If endpoint path is invalid.
        :class:`RouteAlreadyExists`
            If a route to the endpoint path already exists.
        """
        return self.route(path, methods=['GET'])

    def post(self, path: str) -> None:
        """Create a route of type ``POST`` to the router.

        This is a shortcut to ``Router.route(path, methods=['POST'])``.

        Parameters
        ----------
        path: :class:`str`
            The path to the endpoint. It should always start with
            ``/``.

        Raises
        ------
        :class:`InvalidPath`
            If endpoint path is invalid.
        :class:`RouteAlreadyExists`
            If a route to the endpoint path already exists.
        """
        return self.route(path, methods=['POST'])

    def add_router(self, base_path: str, router: Router) -> None:
        """Aggregates the routes from the given router to the current
        router.

        Parameters
        ----------
        base_path: :class:`str`
            The base path that routes should follow.
        router: :class:`Router`
            The router to be added to the current.
        """
        for path, routes in router._routes.items():
            for method, func in routes.items():
                self.route(base_path + path, methods=[method])(func)