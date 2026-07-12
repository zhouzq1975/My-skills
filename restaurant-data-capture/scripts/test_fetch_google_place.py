#!/usr/bin/env python3
"""Regression tests for restaurant-data-capture packet canonicalization."""

from __future__ import annotations

import unittest

import fetch_google_place


class PacketCanonicalizationTests(unittest.TestCase):
    def test_canonicalize_packet_preserves_manual_new_opening_flag(self) -> None:
        packet = {
            "seed": {
                "nameZh": "新店",
                "nameEn": "New Restaurant",
                "addressRaw": "Example Str. 1, Berlin",
                "city": "Berlin",
                "country": "Germany",
            },
            "inferred": {
                "positioning_summary": "Example restaurant focused on noodles.",
                "short_description_zh": "一家新开的面馆。",
                "short_description_en": "A newly opened noodle house.",
                "short_description_de": "Ein neu eröffnetes Nudelhaus.",
                "operating_status": "operating",
                "is_new_opening": True,
            },
        }

        canonical = fetch_google_place.canonicalize_packet(packet)

        self.assertEqual(canonical["packet_meta"]["schemaVersion"], 3)
        self.assertEqual(canonical["inferred"]["operating_status"], "operating")
        self.assertIs(canonical["inferred"]["is_new_opening"], True)

    def test_canonicalize_packet_initializes_new_opening_flag_to_null(self) -> None:
        packet = {
            "seed": {
                "nameEn": "Existing Restaurant",
                "addressRaw": "Example Str. 2, Berlin",
                "city": "Berlin",
                "country": "Germany",
            },
        }

        canonical = fetch_google_place.canonicalize_packet(packet)

        self.assertIn("is_new_opening", canonical["inferred"])
        self.assertIsNone(canonical["inferred"]["is_new_opening"])

    def test_extract_reviews_raw_keeps_only_food_specific_reviews(self) -> None:
        details = {
            "reviews": [
                {
                    "rating": 5,
                    "text": "Great service and nice staff.",
                    "relative_time_description": "2 weeks ago",
                },
                {
                    "rating": 5,
                    "text": "The mapo tofu and dumplings were excellent.",
                    "relative_time_description": "1 month ago",
                },
                {
                    "rating": 4,
                    "text": "麻婆豆腐很好吃，担担面也不错。",
                    "relative_time_description": "3 months ago",
                },
            ]
        }

        rows = fetch_google_place.extract_reviews_raw(details, "en")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["dishTermsRaw"], ["mapo tofu", "dumplings"])
        self.assertEqual(rows[1]["dishTermsRaw"], ["麻婆豆腐", "担担面"])


if __name__ == "__main__":
    unittest.main()
