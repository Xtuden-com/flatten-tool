# -*- coding: utf-8 -*-
"""
Tests of unflatten method of the SpreadsheetInput class from input.py

Tests that only apply for multiple sheets.
"""
from __future__ import unicode_literals
from .test_input_SpreadsheetInput import ListInput
from decimal import Decimal
from collections import OrderedDict
import sys
import pytest
import openpyxl
import datetime
from six import text_type

class TestUnflatten(object):
    def test_basic_sub_sheet(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'ocid': 1,
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'subField/0/testA': 3,
                    }
                ]
            },
            main_sheet_name='custom_main')
        spreadsheet_input.read_sheets()
        assert list(spreadsheet_input.unflatten()) == [
            {'ocid': 1, 'id': 2, 'subField': [{'testA': 3}]}
        ]

    def test_nested_sub_sheet(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'ocid': 1,
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'testA/subField/0/testB': 3,
                    }
                ]
            },
            main_sheet_name='custom_main')
        spreadsheet_input.read_sheets()
        assert list(spreadsheet_input.unflatten()) == [
            {'ocid': 1, 'id': 2, 'testA': {'subField': [{'testB': 3}]}}
        ]

    def test_basic_two_sub_sheets(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    OrderedDict([
                        ('ocid', 1),
                        ('id', 2),
                    ])
                ],
                'sub1': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'sub1Field/0/id': 3,
                        'sub1Field/0/testA': 4,
                    }
                ],
                'sub2': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'sub1Field/0/id': 3,
                        'sub1Field/0/sub2Field/0/testB': 5,
                    }
                ]
            },
            main_sheet_name='custom_main')
        spreadsheet_input.read_sheets()
        unflattened = list(spreadsheet_input.unflatten())
        assert len(unflattened) == 1
        assert set(unflattened[0]) == set(['ocid', 'id', 'sub1Field']) # FIXME should be ordered
        assert unflattened[0]['ocid'] == 1
        assert unflattened[0]['id'] == 2
        assert unflattened[0]['sub1Field'] == [
            {
                'id': 3,
                'testA': 4,
                'sub2Field': [
                    {
                        'testB': 5
                    }
                ]
            }
        ]

    def test_nested_id(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'ocid': 1,
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'subField/0/id': 3,
                        'subField/0/testA/id': 4,
                    }
                ]
            },
            main_sheet_name='custom_main')
        spreadsheet_input.read_sheets()
        assert list(spreadsheet_input.unflatten()) == [
            {'ocid': 1, 'id': 2, 'subField': [{'id': 3, 'testA': {'id': 4}}]}
        ]

    @pytest.mark.xfail()
    def test_missing_columns(self, recwarn):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'ocid': 1,
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'ocid': 1,
                        'id': '',
                        'subField/id': 3,
                        'subField/testA/id': 4,
                    },
                    {
                        'ocid': 1,
                        'id': 2,
                        'subField/id': 3,
                        'subField/testA': 5,
                    }
                ]
            },
            main_sheet_name='custom_main')
        spreadsheet_input.read_sheets()
        unflattened = list(spreadsheet_input.unflatten())
        # We should have a warning about conflicting ID fields
        w = recwarn.pop(UserWarning)
        assert 'no parent id fields populated' in text_type(w.message)
        assert 'Line 2 of sheet sub' in text_type(w.message)
        # Check that following lines are parsed correctly
        assert unflattened == [
            {'ocid': 1, 'id': 2, 'subField': [{'id': 3, 'testA': 5}]}
        ]


class TestUnflattenRollup(object):
    def test_same_rollup(self, recwarn):
        spreadsheet_input = ListInput(
            sheets={
                'main': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'testA/0/id': 3,
                        'testA/0/testB': 4
                    }
                ],
                'testA': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'testA/0/id': 3,
                        'testA/0/testB': 4,
                    }
                ]
            },
            main_sheet_name='main'
        )
        spreadsheet_input.read_sheets()
        unflattened = list(spreadsheet_input.unflatten())
        assert unflattened == [
            {'ocid': 1, 'id': 2, 'testA': [{'id': 3, 'testB': 4}]}
        ]
        # We expect no warnings
        assert recwarn.list == []

    def test_conflicting_rollup(self, recwarn):
        spreadsheet_input = ListInput(
            sheets={
                'main': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'testA/0/id': 3,
                        'testA/0/testB': 4
                    }
                ],
                'testA': [
                    {
                        'ocid': 1,
                        'id': 2,
                        'testA/0/id': 3,
                        'testA/0/testB': 5,
                    }
                ]
            },
            main_sheet_name='main'
        )
        spreadsheet_input.read_sheets()
        unflattened = list(spreadsheet_input.unflatten())
        assert unflattened == [
            {'ocid': 1, 'id': 2, 'testA': [{'id': 3, 'testB': 4}]} # FIXME could be 4 or 5 in future?
        ]
        # We should have a warning about the conflict
        w = recwarn.pop(UserWarning)
        assert 'Conflict between main sheet and sub sheet' in text_type(w.message)


class TestUnflattenEmpty(object):
    def test_sub_sheet_empty(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [],
                'subsheet': [
                    {
                        'ocid': '',
                        'id': '',
                        'testA': '',
                        'testB': '',
                        'testC': '',
                        'testD': '',
                    }
                ]
            },
            main_sheet_name='custom_main')
        spreadsheet_input.read_sheets()
        output = list(spreadsheet_input.unflatten())
        assert len(output) == 0


class TestUnflattenCustomRootID(object):
    def test_basic_sub_sheet(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'custom': 1,
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'custom': 1,
                        'id': 2,
                        'subField/0/testA': 3,
                    }
                ]
            },
            main_sheet_name='custom_main',
            root_id='custom')
        spreadsheet_input.read_sheets()
        assert list(spreadsheet_input.unflatten()) == [
            {'custom': 1, 'id': 2, 'subField': [{'testA': 3}]}
        ]

    def test_nested_sub_sheet(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'custom': 1,
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'custom': 1,
                        'id': 2,
                        'testA/subField/0/testB': 3,
                    }
                ]
            },
            main_sheet_name='custom_main',
            root_id='custom')
        spreadsheet_input.read_sheets()
        assert list(spreadsheet_input.unflatten()) == [
            {'custom': 1, 'id': 2, 'testA': {'subField': [{'testB': 3}]}}
        ]

    def test_basic_two_sub_sheets(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    OrderedDict([
                        ('custom', 1),
                        ('id', 2),
                    ])
                ],
                'sub1': [
                    {
                        'custom': 1,
                        'id': 2,
                        'sub1Field/0/id': 3,
                        'sub1Field/0/testA': 4,
                    }
                ],
                'sub2': [
                    {
                        'custom': 1,
                        'id': 2,
                        'sub1Field/0/id': 3,
                        'sub1Field/0/sub2Field/0/testB': 5,
                    }
                ]
            },
            main_sheet_name='custom_main',
            root_id='custom')
        spreadsheet_input.read_sheets()
        unflattened = list(spreadsheet_input.unflatten())
        assert len(unflattened) == 1
        assert set(unflattened[0]) == set(['custom', 'id', 'sub1Field']) # FIXME should be ordered
        assert unflattened[0]['custom'] == 1
        assert unflattened[0]['id'] == 2
        assert unflattened[0]['sub1Field'] == [
            {
                'id': 3,
                'testA': 4,
                'sub2Field': [
                    {
                        'testB': 5
                    }
                ]
            }
        ]


class TestUnflattenNoRootID(object):
    def test_basic_sub_sheet(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'id': 2,
                        'subField/0/testA': 3,
                    }
                ]
            },
            main_sheet_name='custom_main',
            root_id='')
        spreadsheet_input.read_sheets()
        assert list(spreadsheet_input.unflatten()) == [
            {'id': 2, 'subField': [{'testA': 3}]}
        ]

    def test_nested_sub_sheet(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    {
                        'id': 2,
                    }
                ],
                'sub': [
                    {
                        'id': 2,
                        'testA/subField/0/testB': 3,
                    }
                ]
            },
            main_sheet_name='custom_main',
            root_id='')
        spreadsheet_input.read_sheets()
        assert list(spreadsheet_input.unflatten()) == [
            {'id': 2, 'testA': {'subField': [{'testB': 3}]}}
        ]

    def test_basic_two_sub_sheets(self):
        spreadsheet_input = ListInput(
            sheets={
                'custom_main': [
                    OrderedDict([
                        ('id', 2),
                    ])
                ],
                'sub1': [
                    {
                        'id': 2,
                        'sub1Field/0/id': 3,
                        'sub1Field/0/testA': 4,
                    }
                ],
                'sub2': [
                    {
                        'id': 2,
                        'sub1Field/0/id': 3,
                        'sub1Field/0/sub2Field/0/testB': 5,
                    }
                ]
            },
            main_sheet_name='custom_main',
            root_id='')
        spreadsheet_input.read_sheets()
        unflattened = list(spreadsheet_input.unflatten())
        assert len(unflattened) == 1
        assert unflattened[0]['id'] == 2
        assert unflattened[0]['sub1Field'] == [
            {
                'id': 3,
                'testA': 4,
                'sub2Field': [
                    {
                        'testB': 5
                    }
                ]
            }
        ]
