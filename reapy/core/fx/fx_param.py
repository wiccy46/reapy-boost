from typing import Any, Callable, Dict, Iterator, Optional, Tuple, Union
import reapy
import reapy.reascript_api as RPR
from reapy.core import ReapyObject, ReapyObjectList
from reapy.errors import DistError


class FXParam(float):
    """FX parameter."""

    def __init__(
        self, value: float, parent_list: 'FXParamsList', index: int,
        functions: Dict[str, Dict[str, Callable[..., Any]]]
    ) -> None:
        float.__init__(value)
        self.parent_list = parent_list
        self.index = index
        self.functions = functions

    def __new__(self, value: float, *args: Any, **kwargs: Any) -> 'FXParam':
        return float.__new__(self, value)

    def add_envelope(self) -> 'reapy.Envelope':
        """
        Create envelope for the parameter and return it.

        Returns
        -------
        envelope : Envelope
            New envelope for the parameter.

        Notes
        -----
        If the envelope already exists, the function returns it.
        """
        parent_fx = self.parent_list.parent_fx
        parent = parent_fx.parent
        if isinstance(parent, reapy.Track):
            callback = RPR.GetFXEnvelope  # type:ignore
        else:  # Then it is a Take
            callback = self.functions["GetEnvelope"]
        envelope = reapy.Envelope(
            parent, callback(parent.id, parent_fx.index, self.index, True)
        )
        return envelope

    @property
    def envelope(self) -> Optional['reapy.Envelope']:
        """
        Parameter envelope (or None if it doesn't exist).

        :type: Envelope or NoneType
        """
        parent_fx = self.parent_list.parent_fx
        parent = parent_fx.parent
        if isinstance(parent, reapy.Track):
            callback = RPR.GetFXEnvelope  # type:ignore
        else:  # Then it is a Take
            callback = self.functions["GetEnvelope"]
        envelope = reapy.Envelope(
            parent, callback(parent.id, parent_fx.index, self.index, False)
        )
        if not envelope._is_defined:
            envelope = None
        return envelope

    def format_value(self, value: float) -> str:
        """
        Return human readable string for value.

        It is the way ``value`` would be printed in REAPER GUI if it
        was the actual parameter value. Only works with FX that
        support Cockos VST extensions.

        Parameters
        ----------
        value : float
            Value to format.

        Returns
        -------
        formatted : str
            Formatted value.
        """
        parent_fx = self.parent_list.parent_fx
        parent = parent_fx.parent
        return self.functions["FormatParamValue"](
            parent.id, parent_fx.index, self.index, value, "", 2048
        )[5]

    @property
    def formatted(self) -> str:
        """
        Human readable string for parameter value.

        Only works with FX that support Cockos VST extensions.

        :type: str
        """
        parent_fx = self.parent_list.parent_fx
        parent = parent_fx.parent
        return self.functions["GetFormattedParamValue"](
            parent.id, parent_fx.index, self.index, "", 2048
        )[4]

    @property
    def name(self) -> str:
        """
        Parameter name.

        :type: str
        """
        parent_list = self.parent_list
        name = self.functions["GetParamName"](
            parent_list.parent_id, parent_list.fx_index, self.index, "", 2048
        )[4]
        return name

    @property
    def normalized(self) -> float:
        """
        Normalized FX parameter.

        Attribute can be set with a float, but be careful that since
        floats are immutable, this parameter won't have to right value
        anymore. See Examples below.

        :type: NormalizedFXParam

        Examples
        --------
        Say the parameter range is (0.0, 20.0).

        >>> param = fx.params[0]
        >>> param
        10.0
        >>> param.normalized
        0.5

        If you set the parameter like below, the parameter moves in
        REPAER, but the FXParam object you are using is not valid
        anymore.

        >>> param.normalized = 1
        >>> param, param.normalized
        10.0, 0.5

        You thus have to grab the updated FXParam from the FX like
        below.

        >>> param = fx.params[0]
        >>> param, param.normalized
        20.0, 1.0
        """
        min, max = self.range
        value = (self - min) / (max - min)
        return NormalizedFXParam(
            value, self.parent_list, self.index, self.functions
        )

    @normalized.setter
    def normalized(self, value: float) -> None:
        parent_fx = self.parent_list.parent_fx
        parent = parent_fx.parent
        self.functions["SetParamNormalized"](
            parent.id, parent_fx.id, self.index, value
        )

    @property
    def range(self) -> Tuple[float, float]:
        """
        Parameter range.

        :type: float, float
        """
        parent_list = self.parent_list
        min_, max_ = self.functions["GetParam"](
            parent_list.parent_id, parent_list.fx_index, self.index, 0, 0
        )[-2:]
        return min_, max_


class FXParamsList(ReapyObjectList):
    """
    Container class for a list of FX parameters.

    Parameters can be accessed by name or index.

    Examples
    --------
    >>> params_list = fx.params
    >>> params_list[0]  # Say this is "Dry Gain" parameter
    0.5
    >>> params_list["Dry Gain"]
    0.5
    >>> params_list["Dry Gain"] = 0.1
    >>> params_list[0]
    0.1
    """

    def __init__(
        self,
        parent_fx: Optional[reapy.FX] = None,
        parent_id: Optional[str] = None,
        parent_fx_index: Optional[int] = None
    ) -> None:
        if parent_fx is None:
            parent_fx = reapy.FX(parent_id=parent_id, index=parent_fx_index)
        self.parent_id = parent_fx.parent_id
        self.fx_index = parent_fx.index
        self.functions = parent_fx.functions

    def __getitem__(self, i: Union[str, int]) -> FXParam:
        with reapy.inside_reaper():
            if isinstance(i, str):
                i = self._get_param_index(i)
            n_params = len(self)
            if i >= n_params:
                raise IndexError(
                    "{} has only {} params".format(self.parent_fx, n_params)
                )
            i = i % n_params  # Allows for negative values
        value = self.functions["GetParam"](
            self.parent_id, self.fx_index, i, 0, 0
        )[0]
        param = FXParam(value, self, i, self.functions)
        return param

    def __iter__(self) -> Iterator[FXParam]:
        for i, value in enumerate(self._get_values()):
            yield FXParam(value, self, i, self.functions)

    def __len__(self) -> int:
        length = self.parent_fx.n_params
        return length

    def __setitem__(self, i: Union[str, int], value: float) -> None:
        with reapy.inside_reaper():
            if isinstance(i, str):
                i = self._get_param_index(i)
            n_params = len(self)
            if i >= n_params:
                raise IndexError(
                    "{} has only {} params".format(self.parent_fx, n_params)
                )
            i = i % n_params  # Allows for negative values
        self.functions["SetParam"](self.parent_id, self.fx_index, i, value)

    @reapy.inside_reaper()
    def _get_param_index(self, name: str) -> int:
        try:
            return [fx.name for fx in self].index(name)
        except ValueError:
            raise IndexError(
                "{} has no param named {}".format(self.parent_fx, name)
            )

    @reapy.inside_reaper()
    def _get_values(self) -> List[float]:
        """Return values of all parameters in self."""
        return [
            self.functions["GetParam"](self.parent_id, self.fx_index, i, 0,
                                       0)[0] for i in range(len(self))
        ]

    @property
    def _kwargs(self) -> Dict[str, Union[int, str]]:
        return {"parent_fx_index": self.fx_index, "parent_id": self.parent_id}

    @property
    def parent_fx(self) -> 'reapy.FX':
        """
        Parent FX.

        :type: FX
        """
        fx = reapy.FX(parent_id=self.parent_id, index=self.fx_index)
        return fx


class NormalizedFXParam(FXParam):
    """
    Normalized FX parameter.

    Access it via FXParam.normalized.

    Examples
    --------
    >>> fx.params[0]
    0.0
    >>> fx.params[0].range
    (-2.0, 0.0)
    >>> fx.params[0].normalized
    1.0
    >>> fx.params[0].normalized.range
    (0.0, 1.0)
    """

    def format_value(self, value: float) -> str:
        """
        Return human readable string for value.

        It is the way ``value`` would be printed in REAPER GUI if it
        was the actual parameter value. Only works with FX that
        support Cockos VST extensions.

        Parameters
        ----------
        value : float
            Value to format.

        Returns
        -------
        formatted : str
            Formatted value.
        """
        parent_fx = self.parent_list.parent_fx
        parent = parent_fx.parent
        return self.functions["FormatParamValueNormalized"](
            parent.id, parent_fx.index, self.index, value, "", 2048
        )[5]

    @property
    def range(self) -> Tuple[float, float]:
        """
        Parameter range (always equal to (0.0, 1.0)).
        """
        return (0.0, 1.0)

    @property
    def raw(self) -> 'FXParam':
        """
        Raw (i.e. unnormalized) parameter.

        :type: FXParam
        """
        return self.parent_list[self.index]
