# Copyright 2021 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from rc_django.views import RestView
from rc_django.models import RestProxy
from django.template import loader, TemplateDoesNotExist
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from userservice.user import UserService
from urllib.parse import quote, unquote, urlencode, urlparse, parse_qs
from base64 import b64encode
import logging
import re

logger = logging.getLogger(__name__)


class RestProxyView(RestView):
    template_name = "proxy.html"

    @staticmethod
    def format_search_params(url):
        params = {}
        query_params = parse_qs(urlparse(url).query)
        for param in query_params:
            params[param] = ",".join(query_params[param])
        return params

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = kwargs.get("service")
        service_name = service
        url = "/" + quote(kwargs.get("url", ""))
        headers = kwargs.get("headers", {})
        use_pre = False
        is_image = False
        user_service = UserService()

        if service == 'iasystem':
            headers["Accept"] = "application/vnd.collection+json"
            service_name = 'iasystem_uw'
        elif service == "sws" or service == "gws":
            headers["X-UW-Act-as"] = user_service.get_original_user()
        elif service == "calendar":
            use_pre = True

        proxy = RestProxy(service_name)
        response = proxy.get_api_response(url, headers)

        if (response.status == 200 and
                re.match(r'/idcard/v1/photo/[0-9A-F]{32}', url)):
            # Handle known images
            is_image = True
            content = b64encode(response.data)
        elif use_pre:
            content = response.data
        else:
            content = proxy.formatted

        context.update({
            "url": unquote(url),
            "content": content,
            "json_data": proxy.json,
            "response_code": response.status,
            "time_taken": "{:f} seconds".format(proxy.duration),
            "headers": response.headers,
            "override_user": user_service.get_override_user(),
            "use_pre": use_pre,
            "is_image": is_image,
        })

        try:
            loader.get_template("restclients/extra_info.html")
            context["has_extra_template"] = True
            context["extra_template"] = "restclients/extra_info.html"
        except TemplateDoesNotExist:
            pass

        try:
            search_template_path = re.sub(r"[.?].*$", "", url)
            search_template = "proxy/{}{}.html".format(service,
                                                       search_template_path)
            loader.get_template(search_template)
            context["search_template"] = search_template
            context["search"] = format_search_params(url)
        except TemplateDoesNotExist:
            context["search_template"] = None

        return context

    def get(self, request, *args, **kwargs):
        """
        Fetch an API resource and render it, formatted for a browser.
        """
        # Using args for these URLs for backwards-compatibility
        kwargs["service"] = args[0]
        kwargs["url"] = args[1] if len(args) > 1 else ""

        if request.GET:
            kwargs["url"] += "?" + urlencode(request.GET)

        try:
            context = self.get_context_data(**kwargs)
        except (AttributeError, ImportError):
            return HttpResponse(
                "Missing service: {}".format(kwargs["service"]), status=404)

        return self.render_to_response(context)


class RestSearchView(RestView):
    template_name = "customform.html"

    def get_context_data(self, **kwargs):
        service = kwargs.get("service")
        path = kwargs.get("path", "")

        context = super().get_context_data(**kwargs)
        context["form_template"] = "customform/{}/{}".format(service, path)
        context["form_action"] = reverse("restclients_customform", args=[
            service, path.replace(".html", "")])
        return context

    def get(self, request, *args, **kwargs):
        """
        Renders a custom form for searching a REST service.
        """
        # Using args for these URLs for backwards-compatibility
        kwargs["service"] = args[0]
        kwargs["path"] = args[1] if len(args) > 1 else ""
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Entry point for custom search form submissions.
        Convert form data to actual API urls, and redirect to proxy view.
        """
        service = args[0]
        url = args[1] if len(args) > 1 else ""
        params = {k: v for k, v in request.POST.items() if (
            k != "csrfmiddlewaretoken")}
        requires_query_params = False

        try:
            if service == "book":
                url = "uw/json_utf8_202007.ubs"
                requires_query_params = True
            elif service == "grad":
                requires_query_params = True
            elif service == "hfs":
                url = "myuw/v1/{}".format(request.POST["uwnetid"])
            elif re.match(r'^iasystem', service):
                if url.endswith('/evaluation'):
                    index = url.find('/')
                    service = 'iasystem_' + url[:index]
                    index += 1
                    url = url[index:]
                    requires_query_params = True
            elif service == "myplan":
                url = "student/api/plan/v1/{},{},1,{}".format(
                    request.POST["year"],
                    request.POST["quarter"],
                    request.POST["uwregid"])
            elif service == "libcurrics":
                if "course" == url:
                    url = "currics_db/api/v1/data/{}/{}/{}/{}/{}/{}".format(
                        "course",
                        request.POST["year"],
                        request.POST["quarter"],
                        request.POST["curriculum_abbr"],
                        request.POST["course_number"],
                        request.POST["section_id"])
                elif "default" == url:
                    url = "currics_db/api/v1/data/defaultGuide/{}".format(
                        request.POST["campus"])
            elif service == "libraries":
                url = "mylibinfo/v1/"
                requires_query_params = True
            elif service == "sws":
                if "advisers" == url:
                    url = "student/v5/person/{}/advisers.json".format(
                        request.POST["uwregid"])
            elif service == "uwnetid":
                if "password" == url:
                    url = "nws/v1/uwnetid/{}/password".format(
                        request.POST["uwnetid"])
                elif "subscription" == url:
                    url = "nws/v1/uwnetid/{}/subscription/60,64,105".format(
                        request.POST["uwnetid"])

        except KeyError as ex:
            return HttpResponse("Missing reqired form value: {}".format(ex),
                                status=400)

        url = reverse("restclients_proxy", args=[service, url])
        if requires_query_params:
            url += "?" + urlencode(params)
        return HttpResponseRedirect(url)