"""Offline regression cases for alert thresholds; never accesses Ajax or email."""
import unittest
from html import escape
from playwright.sync_api import sync_playwright
from monitor import observe

def row(category, rate="Regulier", maximum=1, disabled=False):
    options = "".join('<option value="%s">%s</option>' % (n, n) for n in range(maximum + 1))
    return '<tr><th class="category">' + escape(category) + '</th><th><span class="audience-subcat-name">' + escape(rate) + '</span></th><td><select aria-label="Quantity"' + (' disabled' if disabled else '') + '>' + options + '</select></td></tr>'

class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = sync_playwright().start()
        cls.browser = cls.p.chromium.launch()
        cls.page = cls.browser.new_page()
    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.p.stop()
    def check(self, rows, expected, http_status=200):
        self.page.set_content("<h1>Ajax - ADO Den Haag</h1><p>22 November 2026</p><table>" + rows + "</table>")
        status, _ = observe(self.page, http_status)
        self.assertEqual(status, expected)
    def test_observed_single_regular_ticket_does_not_alert(self):
        self.check(row("405 406 420 421 (low)"), "below_threshold")
    def test_two_regular_tickets_alert(self):
        self.check(row("A", maximum=2), "available_indication")
    def test_two_distinct_categories_can_total_two(self):
        self.check(row("A") + row("B"), "available_indication")
    def test_multiple_tariffs_same_inventory_do_not_double_count(self):
        self.check(row("A") + row("A", rate="Official Resale"), "below_threshold")
    def test_official_resale_is_eligible(self):
        self.check(row("A", rate="Official Resale", maximum=2), "available_indication")
    def test_vip_premium_hospitality_do_not_count(self):
        self.check(row("VIP A", maximum=2) + row("Premium B", maximum=2) + row("Hospitality C", maximum=2), "below_threshold")
    def test_disabled_controls_do_not_count(self):
        self.check(row("A", maximum=2, disabled=True), "below_threshold")
    def test_unknown_rate_does_not_count(self):
        self.check(row("A", rate="Unverified package", maximum=2), "below_threshold")
    def test_403_never_means_available(self):
        self.check(row("A", maximum=2), "http_403", http_status=403)
    def test_wrong_event_never_alerts(self):
        self.page.set_content("<p>Ajax - Other club 22 November 2026</p><table>" + row("A", maximum=2) + "</table>")
        self.assertEqual(observe(self.page)[0], "wrong_or_unknown_event")
    def test_unknown_layout_never_reports_sold_out(self):
        self.check("", "unknown_layout")

if __name__ == "__main__":
    unittest.main()
