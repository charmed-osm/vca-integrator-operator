#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.


import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the charm osm-vca-integrator-k8s and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    await ops_test.model.set_config({"update-status-hook-interval": "10s"})

    charm = await ops_test.build_charm(".")
    await ops_test.model.deploy(charm, application_name="osm-vca-integrator-k8s")
    await ops_test.model.wait_for_idle(
        apps=["osm-vca-integrator-k8s"], status="blocked", timeout=1000
    )
    assert (
        ops_test.model.applications["osm-vca-integrator-k8s"].units[0].workload_status == "blocked"
    )

    logger.debug("Setting update-status-hook-interval to 60m")
    await ops_test.model.set_config({"update-status-hook-interval": "60m"})
