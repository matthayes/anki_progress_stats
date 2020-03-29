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

from datetime import datetime
import pytz
import tzlocal
from sqlite3 import dbapi2 as sqlite
from sqlalchemy import create_engine

from progress_stats.compute import get_stats


engine = create_engine('sqlite+pysqlite:///test_collection.anki2', module=sqlite)
conn = engine.connect()


def get_next_day_cutoff_seconds(hour):
    "Return the next cutoff for a particular hour as seconds since epoch."
    local_tz = tzlocal.get_localzone()
    dt_cutoff = local_tz.localize(datetime.now().replace(minute=0, second=0, microsecond=0, hour=hour))

    # TODO doesn't actually work.  if it is 1 am then it doens't chose 4 am of the same day.
    # dt_cutoff += timedelta(days=1)

    epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)
    return (dt_cutoff - epoch).total_seconds()


cutoff = get_next_day_cutoff_seconds(4)  # 4 am cutoff

# TODO this won't work because db_conn has been removed.  Need to pass the table instead.
stats = get_stats(
    db_conn=conn,
    bucket_size_days=30, day_cutoff_seconds=cutoff)
print(stats)


def sum_values(values):
    return sum(y for x, y in values)


print("matured_cards", sum_values(stats["matured_cards"]))
print("net_matured_cards", sum_values(stats["net_matured_cards"]))
print("matured_reviews", sum_values(stats["matured_reviews"]))
print("lost_matured_card", sum_values(stats["lost_matured_card"]))
print("learned_cards", sum_values(stats["learned_cards"]))
