# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from ops.testing import Harness
from pytest_mock import MockerFixture

from charm import VcaIntegratorCharm


@pytest.fixture
def harness():
    osm_vca_integrator_harness = Harness(VcaIntegratorCharm)
    osm_vca_integrator_harness.begin()
    yield osm_vca_integrator_harness
    osm_vca_integrator_harness.cleanup()


def test_on_config_changed(mocker: MockerFixture, harness: Harness):
    pass
