# Copyright 2016 Matthew Hayes

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

    if self.type == 0:
        num_buckets = 30
        bucket_size_days = 1
    elif self.type == 1:
        num_buckets = 52
        bucket_size_days = 7
    else:
        num_buckets = None
        bucket_size_days = 30

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


def _plot(self, data, title, subtitle, bucket_size_days,
          include_cumulative=False,
          color=defaultColor):

    global _num_graphs
    if not data:
        return ""
    cumulative_total = 0
    cumulative_data = []
    max_yaxis = _round_up_max(max(y for x, y in data))
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

    yaxes = [dict(min=0, max=max_yaxis)]

    if include_cumulative:
        yaxes.append(dict(min=0, max=_round_up_max(max(y for x, y in cumulative_data)), position="right"))

    txt += self._graph(
        id="progress-%s" % _num_graphs,
        data=graph_data,
        conf=dict(
            xaxis=dict(max=0.5),
            yaxes=yaxes))

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
