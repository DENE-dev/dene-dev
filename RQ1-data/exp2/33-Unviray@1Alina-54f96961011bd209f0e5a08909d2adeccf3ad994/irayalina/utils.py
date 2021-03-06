"""
irayalina.utils
===============
"""

from flask import request
from flask import render_template as render


def templated(template=None):
    """
    https://flask.palletsprojects.com/patterns/viewdecorators.html#templating-decorator

    Decorate view with this insted of returning render_template obj
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            template_name = template
            if template_name is None:
                template_name = request.endpoint \
                    .replace('.', '/') + '.html'
            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}
            elif not isinstance(ctx, dict):
                return ctx
            return render(template_name, **ctx)

        return decorated_function

    return decorator