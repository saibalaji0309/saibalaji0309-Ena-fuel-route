from unittest import mock

from django.test import TestCase

from stations.models import FuelStation
from stations.repository import get_station_index
from .clients import Route
from .optimizer import Candidate, NoFeasiblePlan, plan_fuel_stops


class OptimizerTests(TestCase):
    def test_cost_is_minimised(self):
        cands = [Candidate(0, 300, 4.0, 1), Candidate(1, 600, 3.0, 1), Candidate(2, 900, 5.0, 1)]
        plan = plan_fuel_stops(cands, 1000, 3.5)
        self.assertAlmostEqual(sum(p.gallons for p in plan), 100)
        self.assertAlmostEqual(sum(p.cost for p in plan), 335.0)

    def test_gap_larger_than_range_fails(self):
        with self.assertRaises(NoFeasiblePlan):
            plan_fuel_stops([Candidate(0, 100, 3.0, 1)], 1000, 3.0)

    def test_short_trip_buys_only_what_is_needed(self):
        plan = plan_fuel_stops([], 200, 3.0)
        self.assertAlmostEqual(plan[0].gallons, 20)


class ApiTests(TestCase):
    def setUp(self):
        get_station_index.cache_clear()
        for i, lon in enumerate([-97.0, -93.0]):
            FuelStation.objects.create(opis_id=i, name=f"S{i}", address="I-X", city="C", state="KS",
                                       price=3.0 + i * 0.1, latitude=40.0, longitude=lon)

    def test_route_endpoint(self):
        coords = [(40.0, -100.0 + i * 0.1) for i in range(101)]
        route = Route(530.0, 8.0, "", coords)
        with mock.patch("trips.service.geocode", side_effect=[(40.0, -100.0), (40.0, -90.0)]), \
             mock.patch("trips.service.get_route", return_value=route):
            resp = self.client.get("/api/route/", {"start": "A", "finish": "B"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertAlmostEqual(body["summary"]["total_gallons"], 53.0, places=1)
        self.assertGreater(body["summary"]["total_fuel_cost_usd"], 0)

    def test_missing_params(self):
        self.assertEqual(self.client.get("/api/route/").status_code, 400)


class FrontendTests(TestCase):
    def test_home_page_served(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fuel Route Planner")
