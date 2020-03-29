# Copyright 2016-2020 Matthew Hayes

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
import math
from .compute import get_stats
from anki.lang import _


colYoung = "#7c7"
colMature = "#070"
colLearn = "#00F"
defaultColor = "#0F0"

_num_graphs = 0


def progressGraphs(*args, **kwargs):
    self = args[0]
    old = kwargs['_old']

    # Try to use get_start_end_chunk if it exists to get the bucketing parameters
    # so the plugin graphs are consistent with Anki's other graphs.  This function only
    # exists for recent versions of Anki.
    if hasattr(self, "get_start_end_chunk"):
        start_not_used, num_buckets, bucket_size_days = self.get_start_end_chunk()

    # Fallback for older versions of Anki without this method.  Backporting the newer logic is
    # a bit complicated.  Note that the fallback values for type 2 don't work well for decks where
    # the deck life is very short (e.g. one or two months), but we'll just have to live with this.
    # The best option is for users to use Anki 2.1.
    else:
        if self.type == 0:
            # type 0 = past month
            num_buckets = 31
            bucket_size_days = 1
        elif self.type == 1:
            # type 1 = past year
            num_buckets = 52
            bucket_size_days = 7
        else:
            # type 2 = deck life
            num_buckets = None
            bucket_size_days = 31

    stats = get_stats(
        db_table=self.col.db,
        bucket_size_days=bucket_size_days, num_buckets=num_buckets,
        day_cutoff_seconds=self.col.sched.dayCutoff, additional_filter=self._revlogLimit())

    result = old(self)

    result += _plot(self,
                    stats["learned_cards"],
                    "Learned Cards",
                    "Number of cards that were learned",
                    bucket_size_days,
                    include_cumulative=True,
                    color=colLearn)

    result += _plot(self,
                    stats["net_matured_cards"],
                    "Net Matured Cards",
                    "Net increase in number of mature cards (matured cards - lost matured cards)",
                    bucket_size_days,
                    include_cumulative=True,
                    color=colMature)

    result += _plot(self,
                    stats["matured_cards"],
                    "Matured Cards",
                    "Number of cards that matured",
                    bucket_size_days,
                    color=colMature)

    result += _plot(self,
                    stats["lost_matured_card"],
                    "Matured Cards Lost",
                    "Number of cards that lost maturity",
                    bucket_size_days,
                    color=colYoung)

    return result


def _round_up_max(max_val):
    "Rounds up a maximum value."

    # Prevent zero values raising an error.  Rounds up to 10 at a minimum.
    max_val = max(10, max_val)

    e = int(math.log10(max_val))
    if e >= 2:
        e -= 1
    m = 10**e
    return math.ceil(float(max_val) / m) * m


def _round_down_min(min_val):
    "Rounds down a minimum value."

    # Minimum should not be positive
    min_val = min(0, min_val)

    if not min_val:
        return 0

    return -1 * _round_up_max(-1 * min_val)


def _plot(self, data, title, subtitle, bucket_size_days,
          include_cumulative=False,
          color=defaultColor):

    global _num_graphs
    if not data:
        return ""
    cumulative_total = 0
    cumulative_data = []
    for (x, y) in data:
        cumulative_total += y
        cumulative_data.append((x, cumulative_total))

    txt = self._title(_(title), _(subtitle))

    graph_data = [dict(data=data, color=color)]

    if include_cumulative:
        graph_data.append(
            dict(data=cumulative_data,
                 color=color,
                 label=_("Cumulative"),
                 yaxis=2,
                 bars={'show': False},
                 lines=dict(show=True),
                 stack=False))

    yaxes = [dict(min=_round_down_min(min(y for x, y in data)),
                  max=_round_up_max(max(y for x, y in data)))]

    if include_cumulative:
        yaxes.append(dict(min=_round_down_min(min(y for x, y in cumulative_data)),
                          max=_round_up_max(max(y for x, y in cumulative_data)),
                          position="right"))

    graph_kwargs = {
        "id": "progress-%s" % _num_graphs,
        "data": graph_data,
        "conf": dict(
            xaxis=dict(max=0.5, tickDecimals=0),
            yaxes=yaxes)
    }

    # In recent versions of Anki, an xunit arg was added to _graph to control the tick
    # labelling.  The old version picked the tick labels based on the graph type (last month, last year,
    # or deck life).  Now for deck life it picks the appropriate bucket size based on the age of the deck.
    try:
        if "xunit" in inspect.signature(self._graph).parameters:
            graph_kwargs["xunit"] = bucket_size_days
    except Exception:
        pass

    txt += self._graph(**graph_kwargs)

    _num_graphs += 1

    text_lines = []

    self._line(
        text_lines,
        _("Average"),
        _("%(avg_cards)0.1f cards/day") % dict(avg_cards=cumulative_total / float(len(data) * bucket_size_days)))

    if include_cumulative:
        self._line(
            text_lines,
            _("Total"),
            _("%(total)d cards") % dict(total=cumulative_total))

    txt += self._lineTbl(text_lines)

    return txt
