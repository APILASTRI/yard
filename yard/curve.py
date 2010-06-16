"""
Curve classes used in YARD.

This package contains implementations for all the curves YARD can plot.
At the time of writing, this includes:

    - ROC curves
    - CROC curves
    - Precision-recall curves
    - Accumulation curves
"""

__author__  = "Tamas Nepusz"
__email__   = "tamas@cs.rhul.ac.uk"
__copyright__ = "Copyright (c) 2010, Tamas Nepusz"
__license__ = "MIT"

from itertools import izip
from yard.data import BinaryConfusionMatrix, BinaryClassifierData
from yard.transform import ExponentialTransformation
from yard.utils import axis_label

class Curve(object):
    """Class representing an arbitrary curve on a 2D space.

    At this stage, a curve is nothing else but a series of points.
    """

    def __init__(self, points):
        """Constructs a curve with the given points. `points` must be
        an iterable of 2-tuples containing the coordinates of the points.
        """
        self._points = None
        self.points = points

    def auc(self):
        """Returns the area under the curve.
        
        The area is calculated using a trapezoidal approximation to make the
        AUC of the `ROCCurve` class relate to the Gini coefficient (where
        G1 + 1 = 2 * AUC).
        """
        points = self.points
        auc = sum((y0+y1) / 2. * (x0-x1) \
                  for (x0, y0), (x1, y1) in izip(points, points[1:]))
        return auc

    def coarsen(self, **kwds):
        """Coarsens the curve in-place.

        This method is useful before plotting a curve that consists
        of many data points that are potentially close to each other.
        The method of coarsening is defined by the keyword arguments
        passed to this function.

        There are two different coarsening methods. The first
        method is invoked as ``coarsen(every=k)`` (where `k` is an
        integer) and it will keep every `k`th point from the curve.
        You can also call ``coarsen(until=k)`` which will keep on
        removing points from the curve (approximately evenly) until
        only `k` points remain. If there are less than `k` points
        initially, the curve will not be changed.
        """

        # Note: we will always keep the first and the last element

        if "every" in kwds and "until" in kwds:
            raise TypeError("use either every=... or until=...")
        if "every" not in kwds and "until" not in kwds:
            raise TypeError("use either every=... or until=...")

        points = self.points
        if not points:
            return

        if "every" in kwds:
            k = int(kwds["every"])
            self._points = points[::k]
            if len(points) % k != 0:
                self._points.append(points[-1])
            return

        k = int(kwds["until"])
        n = len(points)
        step = (n-1) / (k-1.)
        result = [points[int(idx*step)] for idx in xrange(1, k-1)]
        result.append(points[-1])
        self._points = result

    def get_empty_figure(self, *args, **kwds):
        """Returns an empty `matplotlib.Figure` that can be used to show the
        curve. The arguments of this function are passed on intact to the
        constructor of `matplotlib.Figure`, except these (which are interpreted
        here):

            - `title`: the title of the figure.
            - `xlabel`: the label of the X axis.
            - `ylabel`: the label of the Y axis.

        These must be given as keyword arguments.
        """
        import matplotlib.pyplot as plt

        # Extract the keyword arguments handled here
        kwds_extra = dict(xlabel=None, ylabel=None, title=None)
        for name in kwds_extra.keys():
            if name in kwds:
                kwds_extra[name] = kwds[name]
                del kwds[name]

        # Construct the figure
        fig = plt.figure(*args, **kwds)

        # Create the axes, set the axis labels and the plot title
        axes = fig.add_subplot(111)
        for name, value in kwds_extra.iteritems():
            if value is not None:
                getattr(axes, "set_%s" % name)(value)

        # axes.set_xbound(0.0, 1.0)
        # axes.set_ybound(0.0, 1.0)
        return fig

    def get_figure(self, *args, **kwds):
        """Returns a `matplotlib.Figure` that shows the curve.
        The arguments of this function are passed on intact to
        `get_empty_figure()`, except the following which are
        interpreted here:
            
            - `legend`: whether we want a legend on the figure or not.
              If ``False``, no legend will be shown. If ``True``,
              `matplotlib` will try to place the legend in an
              optimal position. If an integer or string, it will be
              interpreted as a location code by `matplotlib`.
        """
        if "legend" in kwds:
            legend = kwds["legend"]
            del kwds["legend"]

        # Get an empty figure and its axes, and plot the curve on the axes
        fig = self.get_empty_figure(*args, **kwds)
        self.plot_on_axes(fig.get_axes()[0], legend=legend)
        return fig

    def plot_on_axes(self, axes, style='r-', legend=True):
        """Plots the curve on the given `matplotlib.Axes` object.
        `style` specifies the style of the curve using ordinary
        ``matplotlib`` conventions. `legend` specifies the position
        where the legend should be added. ``False`` or ``None``
        means no legend.
        """
        # Plot the points
        xs, ys = zip(*self.points)
        curve = axes.plot(xs, ys, style)

        # Create the legend
        if legend is True:
            legend = 0
        if legend is not None and legend is not False:
            label = self._data.title
            if label is not None:
                axes.legend(curve, (label, ), legend)

        return curve

    @property
    def points(self):
        """Returns the points of this curve as a list of 2-tuples.
        
        The returned list is the same as the list used internally in
        the instance. Don't modify it unless you know what you're doing.
        """
        return self._points

    @points.setter
    def points(self, points):
        """Sets the points of this curve. The method makes a copy of the
        given iterable."""
        self._points = [tuple(point) for point in points]

    def show(self, *args, **kwds):
        """Constructs and shows a `matplotlib.Figure` that plots the
        curve. If you need the figure itself for further manipulations,
        call `get_figure()` instead of this method.

        The arguments of this function are passed on intact to
        `get_figure()`.
        """
        self.get_figure(*args, **kwds).show()

    def transform(self, transformation):
        """Transforms the curve in-place by sending all the points to a given
        callable one by one. The given callable must expect two real numbers
        and return the transformed point as a tuple."""
        self._points = [transformation(*point) for point in self._points]

    def transform_x(self, transformation):
        """Transforms the X axis of the curve in-place by sending all the
        points to a given callable one by one. The given callable must expect
        a single real number and return the transformed value."""
        self._points = [(transformation(x), y) for x, y in self._points]

    def transform_y(self, transformation):
        """Transforms the Y axis of the curve in-place by sending all the
        points to a given callable one by one. The given callable must expect
        a single real number and return the transformed value."""
        self._points = [(x, transformation(y)) for x, y in self._points]


class BinaryClassifierPerformanceCurve(Curve):
    """Class representing a broad class of binary classifier performance
    curves.

    By using this class diretly, you are free to specify what's on the X
    and Y axes of the plot. If you are interested in ROC curves, see
    `ROCCurve`, which is a subclass of this class. If you are interested
    in precision-recall curves, see `PrecisionRecallCurve`, which is also
    a subclass. Accumulation curves are implemented in `AccumulationCurve`.
    """

    def __init__(self, data, x_func, y_func):
        """Constructs a binary classifier performance curve from the given
        dataset using the two given measures on the X and Y axes.

        The dataset must contain ``(x, y)`` pairs where `x` is a predicted
        value and `y` defines whether the example is positive or negative.
        When `y` is less than or equal to zero, it is considered a negative
        example, otherwise it is positive. ``False`` also means a negative
        and ``True`` also means a positive example. The dataset can also
        be an instance of :class:`BinaryClassifierData`.

        `x_func` and `y_func` must either be unbound method instances of
        the `BinaryConfusionMatrix` class, or functions that accept
        `BinaryConfusionMatrix` instances as their only arguments and
        return a number.
        """
        self._data = None
        self._points = None
        self.x_func = x_func
        self.y_func = y_func

        if not hasattr(self.x_func, "__call__"):
            raise TypeError, "x_func must be callable"
        if not hasattr(self.y_func, "__call__"):
            raise TypeError, "y_func must be callable"

        self.data = data

    def _calculate_points(self):
        """Returns the actual points of the curve as a list of tuples."""
        x_func, y_func = self.x_func, self.y_func
        self._points = [(x_func(mat), y_func(mat)) for _, mat in \
                self._data.iter_confusion_matrices()]

    @property
    def data(self):
        """Returns the data points from which we generate the curve"""
        return self._data

    @data.setter
    def data(self, data):
        """Sets the data points from which we generate the curve."""
        if isinstance(data, BinaryClassifierData):
            self._data = data
        else:
            self._data = BinaryClassifierData(data)
        self._calculate_points()

    def get_empty_figure(self, *args, **kwds):
        """Returns an empty `matplotlib.Figure` that can be used
        to show the classifier curve. The arguments of this function are
        passed on intact to the constructor of `matplotlib.Figure`,
        except these (which are interpreted here):

            - `title`: the title of the figure.
            - `xlabel`: the label of the X axis. If omitted, we will
              try to infer it from `self.x_func`.
            - `ylabel`: the label of the Y axis. If omitted, we will
              try to infer it from `self.y_func`.

        These must be given as keyword arguments.

        Axis labels are inferred from the function objects that were
        used to obtain the points of the curve; in particular, this method
        is looking for an attribute named ``__axis_label__``, attached to
        the function objects. You can attach such an attribute easily
        by using `yard.utils.axis_label` as a decorator.
        """

        # Infer the labels of the X and Y axes
        def infer_label(func):
            try:
                return getattr(func, "__axis_label__")
            except AttributeError:
                return func.__name__

        if "xlabel" not in kwds:
            kwds["xlabel"] = infer_label(self.x_func)
        if "ylabel" not in kwds:
            kwds["ylabel"] = infer_label(self.y_func)

        return super(BinaryClassifierPerformanceCurve, self).\
                     get_empty_figure(*args, **kwds)


class ROCCurve(BinaryClassifierPerformanceCurve):
    """Class representing a ROC curve.
    
    A ROC curve plots the true positive rate on the Y axis versus
    the false positive rate on the X axis.
    """

    def __init__(self, data):
        """Constructs a ROC curve from the given dataset.

        The dataset must contain ``(x, y)`` pairs where `x` is a predicted
        value and `y` defines whether the example is positive or negative.
        When `y` is less than or equal to zero, it is considered a negative
        example, otherwise it is positive. ``False`` also means a negative
        and ``True`` also means a positive example. The dataset can also
        be an instance of `BinaryClassifierData`.
        """
        super(ROCCurve, self).__init__(data, BinaryConfusionMatrix.fpr,
            BinaryConfusionMatrix.tpr)

    def get_empty_figure(self, *args, **kwds):
        """Returns an empty `matplotlib.Figure` that can be used
        to show the ROC curve. The arguments of this function are
        passed on intact to the constructor of `matplotlib.Figure`,
        except these (which are interpreted here):
            
            - `title`: the title of the figure.
            - `xlabel`: the label of the X axis.
            - `ylabel`: the label of the Y axis.
            - `no_discrimination_line`: if ``True``, the no discrimination
              line will be drawn. If ``False``, it won't be drawn. If
              a string, it is interpreted as a line style by
              ``matplotlib`` and this line style will be used to draw
              the no discrimination line. If it is a tuple, the first
              element of the tuple will be interpreted as the color
              and the second will be interpreted as the line style
              by ``matplotlib``.

        These must be given as keyword arguments.
        """
        if "no_discrimination_line" in kwds:
            no_discrimination_line = kwds["no_discrimination_line"]
            del kwds["no_discrimination_line"]
        else:
            no_discrimination_line = ("#444444", ":")

        # Create the figure by calling the superclass
        fig = super(ROCCurve, self).get_empty_figure(*args, **kwds)
        axes = fig.get_axes()[0]

        # Plot the no-discrimination line
        if no_discrimination_line:
            if isinstance(no_discrimination_line, (tuple, list)):
                color, linestyle = no_discrimination_line
                axes.plot([0, 1], color=color, linestyle=linestyle)
            else:
                axes.plot([0, 1], no_discrimination_line)

        return fig


class PrecisionRecallCurve(BinaryClassifierPerformanceCurve):
    """Class representing a precision-recall curve.
    
    A precision-recall curve plots precision on the Y axis versus
    recall on the X axis.
    """

    def __init__(self, data):
        """Constructs a precision-recall curve from the given dataset.

        The dataset must contain ``(x, y)`` pairs where `x` is a predicted
        value and `y` defines whether the example is positive or negative.
        When `y` is less than or equal to zero, it is considered a negative
        example, otherwise it is positive. ``False`` also means a negative
        and ``True`` also means a positive example. The dataset can also
        be an instance of `BinaryClassifierData`.
        """
        super(PrecisionRecallCurve, self).__init__(data,
            BinaryConfusionMatrix.recall, BinaryConfusionMatrix.precision)


class AccumulationCurve(BinaryClassifierPerformanceCurve):
    """Class representing an accumulation curve.
    
    An accumulation curve plots the true positive rate on the Y axis
    versus the fraction of data classified as positive on the X axis.
    """

    def __init__(self, data):
        """Constructs an accumulation curve from the given dataset.

        The dataset must contain ``(x, y)`` pairs where `x` is a predicted
        value and `y` defines whether the example is positive or negative.
        When `y` is less than or equal to zero, it is considered a negative
        example, otherwise it is positive. ``False`` also means a negative
        and ``True`` also means a positive example. The dataset can also
        be an instance of `BinaryClassifierData`.
        """
        super(PrecisionRecallCurve, self).__init__(data,
            BinaryConfusionMatrix.fdp, BinaryConfusionMatrix.tpr)


class CROCCurve(BinaryClassifierPerformanceCurve):
    """Class representing a concentrated ROC curve.
    
    A CROC curve plots the true positive rate on the Y axis versus
    the false positive rate on the X axis, but it transforms the X axis
    in order to give more emphasis to the left hand side of the X axis
    (close to zero).
    """

    def __init__(self, data, alpha = 7):
        """Constructs a CROC curve from the given dataset.

        The dataset must contain ``(x, y)`` pairs where `x` is a predicted
        value and `y` defines whether the example is positive or negative.
        When `y` is less than or equal to zero, it is considered a negative
        example, otherwise it is positive. ``False`` also means a negative
        and ``True`` also means a positive example. The dataset can also
        be an instance of `BinaryClassifierData`.

        `alpha` is the magnification factor that defines how much do we want
        to focus on the left side of the X axis. The default `alpha`=7
        transforms a FPR of 0.1 to 0.5.
        """
        self._transformation = ExponentialTransformation(alpha)
        super(CROCCurve, self).__init__(data, self._transformed_fpr,
            BinaryConfusionMatrix.tpr)

    @axis_label("Transformed false positive rate")
    def _transformed_fpr(self, matrix):
        """Internal function that returns the transformed FPR value from the
        given confusion matrix that should be plotted on the X axis."""
        return self._transformation(matrix.fpr())

    def get_empty_figure(self, *args, **kwds):
        """Returns an empty `matplotlib.Figure` that can be used
        to show the ROC curve. The arguments of this function are
        passed on intact to the constructor of `matplotlib.Figure`,
        except these (which are interpreted here):
            
            - `title`: the title of the figure.
            - `xlabel`: the label of the X axis.
            - `ylabel`: the label of the Y axis.
            - `no_discrimination_curve`: if ``True``, the no discrimination
              curve will be drawn. If ``False``, it won't be drawn. If
              a string, it is interpreted as a line style by
              ``matplotlib`` and this line style will be used to draw
              the no discrimination line. If it is a tuple, the first
              element of the tuple will be interpreted as the color
              and the second will be interpreted as the line style
              by ``matplotlib``.

        These must be given as keyword arguments.
        """
        if "no_discrimination_curve" in kwds:
            no_discrimination_curve = kwds["no_discrimination_curve"]
            del kwds["no_discrimination_curve"]
        else:
            no_discrimination_curve = ("#444444", ":")

        # Create the figure by calling the superclass
        fig = super(CROCCurve, self).get_empty_figure(*args, **kwds)
        axes = fig.get_axes()[0]

        # Plot the no-discrimination curve
        if no_discrimination_curve:
            ys = [y / 100. for y in xrange(101)]
            xs = [self._transformation(y) for y in ys]
            if isinstance(no_discrimination_curve, (tuple, list)):
                color, linestyle = no_discrimination_curve
                axes.plot(xs, ys, color=color, linestyle=linestyle)
            else:
                axes.plot(xs, ys, no_discrimination_curve)

        return fig



