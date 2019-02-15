from reapy import reascript_api as RPR

class AutomationItem:

    def __init__(self, envelope, index):
        self.envelope_id = envelope.id
        self.index = index
        
    @property
    def length(self):
        """
        Return item length in seconds.
        
        Returns
        -------
        length : float
            Item length in seconds.
        """
        length = RPR.GetSetAutomationItemInfo(
            self.envelope_id, self.index, "D_LENGTH", 0, False
        )
        return length
        
    @length.setter
    def length(self, length):
        """
        Set item length.
        
        Parameters
        ----------
        length : float
            New item length in seconds.
        """
        success = RPR.GetSetAutomationItemInfo(
            self.envelope_id, self.index, "D_LENGTH", length, True
        )