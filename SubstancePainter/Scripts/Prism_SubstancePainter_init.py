# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism-Plugin_SubstancePainter.


from Prism_SubstancePainter_Variables import Prism_SubstancePainter_Variables
from Prism_SubstancePainter_externalAccess_Functions import (
    Prism_SubstancePainter_externalAccess_Functions,
)
from Prism_SubstancePainter_Functions import Prism_SubstancePainter_Functions
from Prism_SubstancePainter_Integration import Prism_SubstancePainter_Integration


class Prism_Plugin_SubstancePainter(
    Prism_SubstancePainter_Variables,
    Prism_SubstancePainter_externalAccess_Functions,
    Prism_SubstancePainter_Functions,
    Prism_SubstancePainter_Integration,
):
    """Main SubstancePainter plugin class (loaded state).
    
    Represents the fully loaded SubstancePainter plugin when running inside SubstancePainter.
    Provides complete functionality including scene management, rendering,
    and integration with Prism pipeline.
    
    Inherits from:
        Prism_SubstancePainter_Variables: Plugin configuration.
        Prism_SubstancePainter_externalAccess_Functions: External access methods.
        Prism_SubstancePainter_Functions: Core SubstancePainter functionality.
        Prism_SubstancePainter_Integration: Installation/integration management.
    """
    def __init__(self, core):
        """Initialize loaded SubstancePainter plugin.
        
        Args:
            core: PrismCore instance.
        """
        Prism_SubstancePainter_Variables.__init__(self, core, self)
        Prism_SubstancePainter_externalAccess_Functions.__init__(self, core, self)
        Prism_SubstancePainter_Functions.__init__(self, core, self)
        Prism_SubstancePainter_Integration.__init__(self, core, self)
