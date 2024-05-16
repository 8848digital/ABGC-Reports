app_name = "abgc_reports"
app_title = "Abgc Reports"
app_publisher = "8848digital.llp"
app_description = "ABGC's Customise Reports"
app_email = "hrishikesh@8848digital.com"
app_license = "MIT"

# Includes in <head>
# ------------------

fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [
			[
				"dt",
				"in",
				(
					# Core Doctypes
					"Asset Repair"
				),
			]
		],
	},
	{
		"doctype": "Client Script",
		"filters": [
			[
				"dt",
				"in",
				(
					# Core Doctypes
					"Asset Repair"
				),
			]
		],
	},
    {
		"doctype": "Property Setter",
		"filters": {"module": ["in", "Abgc Reports"]}
	},
]

# include js, css files in header of desk.html
# app_include_css = "/assets/abgc_reports/css/abgc_reports.css"
# app_include_js = "/assets/abgc_reports/js/abgc_reports.js"

# include js, css files in header of web template
# web_include_css = "/assets/abgc_reports/css/abgc_reports.css"
# web_include_js = "/assets/abgc_reports/js/abgc_reports.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "abgc_reports/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Customer" : "customization/customer/customer.js",
    "Supplier" : "customization/supplier/supplier.js"
}
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "abgc_reports.utils.jinja_methods",
# 	"filters": "abgc_reports.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "abgc_reports.install.before_install"
# after_install = "abgc_reports.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "abgc_reports.uninstall.before_uninstall"
# after_uninstall = "abgc_reports.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "abgc_reports.utils.before_app_install"
# after_app_install = "abgc_reports.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "abgc_reports.utils.before_app_uninstall"
# after_app_uninstall = "abgc_reports.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "abgc_reports.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Asset Repair": "abgc_reports.abgc_reports.override_asset_repair.OverrideAssetRepair"
	# 	"ToDo": "custom_app.overrides.CustomToDo"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	# 	"*": {
	# 		"on_update": "method",
	# 		"on_cancel": "method",
	# 		"on_trash": "method"
	# 	}
	"Asset Repair": {
		# "validate": "abgc_reports.abgc_reports.custom.fetch_total_repair_cost",
		"before_submit": "abgc_reports.abgc_reports.custom.create_gl_entry"
	},
    "Customer":{
        "before_save": "abgc_reports.customization.customer.customer.before_save"
	},
    "Supplier":{
        "before_save": "abgc_reports.customization.supplier.supplier.before_save"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"abgc_reports.tasks.all"
# 	],
# 	"daily": [
# 		"abgc_reports.tasks.daily"
# 	],
# 	"hourly": [
# 		"abgc_reports.tasks.hourly"
# 	],
# 	"weekly": [
# 		"abgc_reports.tasks.weekly"
# 	],
# 	"monthly": [
# 		"abgc_reports.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "abgc_reports.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "abgc_reports.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "abgc_reports.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["abgc_reports.utils.before_request"]
# after_request = ["abgc_reports.utils.after_request"]

# Job Events
# ----------
# before_job = ["abgc_reports.utils.before_job"]
# after_job = ["abgc_reports.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"abgc_reports.auth.validate"
# ]