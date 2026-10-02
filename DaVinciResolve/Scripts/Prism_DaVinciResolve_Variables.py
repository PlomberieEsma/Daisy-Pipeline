import os


class Prism_DaVinciResolve_Variables(object):
    """ DaVinciResolve plugin configuration and metadata.
    
    Defines plugin properties including version, supported file formats,
    render passes for various renderers, and color scheme.
    
    Attributes:
        version: Plugin version string.
        pluginName: Name of the plugin.
        pluginType: Type of plugin (App).
        appShortName: Short name for the application.
        appType: Type of application (3d).
        hasQtParent: Whether the app has Qt parent.
        sceneFormats: List of supported scene file extensions.
        outputFormats: List of supported output file formats.
        appSpecificFormats: Combined list of scene and specific formats.
        appColor: RGB color values for the plugin.
        colorButtonWithStyleSheet: Whether to use stylesheet for color buttons.
        pluginDirectory: Path to plugin directory.
        appIcon: Path to application icon.
    """
    
    def __init__(self, core, plugin):
        """Initialize SubstancePainter plugin variables.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.version = "v2.1.2.1"
        self.pluginName = "DaVinciResolve"
        self.pluginType = "App"
        self.appShortName = "DVR"
        self.appType = "3d"
        self.hasQtParent = True
        self.sceneFormats = [".drp", ".DRP", ".dra", ".DRA"]
        self.appSpecificFormats = self.sceneFormats
        self.outputFormats = [".mov", ".mp4"]
        self.appColor = [205, 227, 40]
        self.hasFrameRange = True
        self.renderPasses = []
        self.platforms = ["Windows"]
        self.pluginDirectory = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self.appIcon = os.path.join(self.pluginDirectory, "Resources", "DVRLogo.png")
