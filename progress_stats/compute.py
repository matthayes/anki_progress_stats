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

from collections import namedtuple, defaultdict


# an individual review of a card with a bucket_index representing the time period the review
# occurred in (e.g. which day, month, etc.)
CardReview = namedtuple('CardReview', ['id', 'first_learned_id', 'bucket_index', 'cid', 'ease',
                        'ivl', 'lastIvl', 'type'])


# all the reviews for a particular card and length of time (e.g. day, week, etc.)
CardReviewsForBucket = namedtuple('CardReviewsForBucket', ['bucket_index', 'cid', 'reviews'])


class ProgressStats:
    """Tracks stats for a particular length of time (e.g. day, week, etc.).

    matured_card: The number of cards that began as not mature and ended as mature.
    matured_reviews: The number of reviews during the length of time where a card matured.
    lost_matured_card: The number of cards that began as mature and ended as not mature.
    learned_cards: The number of cards that began in the learning phase and later exited this phase."""

    def __init__(self):
        self.matured_cards = 0
        self.matured_reviews = 0
        self.lost_matured_card = 0
        self.learned_cards = 0

    def __repr__(self):
        return "(matured_cards=%s, matured_reviews=%s, lost_matured_card=%s, learned_cards=%s)" % \
            (self.matured_cards, self.matured_reviews, self.lost_matured_card, self.learned_cards)


# all the stats for a particular length of time (e.g. day, week, etc.)
BucketStats = namedtuple('BucketStats', ['bucket_index', 'stats'])


def _get_reviews(db_table, bucket_size_days, day_cutoff_seconds, num_buckets=None, additional_filter=None):
    """Fetches all the reviews over a period of time and buckets them by (bucket_index, cid), where
    cid is the card ID and bucket_index where 0 is today, -1 is yesterday, etc.

    bucket_size_days represents the size of each bucket measusured in days.  So a value of 1 buckets per day,
    a value of 7 buckets per week, etc.

    day_cutoff_seconds is the cutoff measured in seconds since epoch for the start of the next day.  So, for example,
    if the cutoff is 4 am then this should be tomorrow at 4 am.

    num_buckets is the (optional) number of buckets, which indicates how many reviews to fetch.  Enough reviews are
    fetched to fill all the buckets.  So, for example, if bucket_size_days is 1 and num_buckets is 30 this fetches
    the last month of reviews.

    db_table is the table used to fetch from the review logs.

    additional_filter is an (optiona) filter added to the SQL WHERE clause that limits which reviews to fetch.
    This can be used to limit the reviews to a particular deck, for example.
    """

    # Set up the overall WHERE clause for the query, which filters out reviews older than the desired time window
    # and includes whatever other additional filters where provided (e.g. filter on cards belonging to a particular
    # deck).

    # The earlier time that will be used for graphing.  Any reviews earlier than this are only used to determine
    # when each card was first learned.
    id_cutoff = None

    filters = []
    if num_buckets:
        id_cutoff = (day_cutoff_seconds - (bucket_size_days * num_buckets * 86400)) * 1000
        # Get all recent reviews and any earlier reviews where the card was learned.  We need to query
        # earlier reviews because Anki's type does not appear to be reliable.  That is, you can't assume
        # that if the type is learning (type = 0) and the ivl becomes positive that this means the card
        # was learned for the first time.
        filters.append("(rl.id >= %d OR (rl.id < %d AND rl.ivl > 0 AND rl.lastIvl < 0))" % (id_cutoff, id_cutoff))
    if additional_filter:
        filters.append(additional_filter)
    where_clause = "WHERE %s" % (" AND ".join(filters)) if filters else ""

    # id: The time at which the review was conducted, in epoch time (milliseconds)
    # cid: The ID of the card that was reviewed.  Also equals card creation time (milliseconds).
    # ivl: The new interval that the card was pushed to after the review.
    #      Positive values are in days; negative values are in seconds (for learning cards).
    # lastIvl: The interval the card had before the review. Cards introduced for the first time
    #          have a last interval equal to the Again delay.
    # ease: 1 for Again, 4 for Easy
    # type: This is 0 for learning cards, 1 for review cards, 2 for relearn cards, and 3 for "cram"
    #       cards (cards being studied in a filtered deck when they are not due).

    # Convert the time to the day, where 0 is today (i.e. after the cutoff for today), -1 is yesterday, etc.
    # We add 0.5 and round in order to round up.

    query = """\
      SELECT rl.id,
             CAST(round(( (rl.id/1000.0 - %d) / 86400.0 / %d ) + 0.5) as int)
               as bucket_index,
             rl.cid, rl.ease, rl.ivl, rl.lastIvl, rl.type
      FROM revlog rl
      %s
      ORDER BY rl.id ASC;
      """ % (day_cutoff_seconds, bucket_size_days, where_clause)

    result = db_table.all(query)

    # Maps cid to the id where the card was first learned.
    first_learned = {}

    all_reviews_for_bucket = {}
    for _id, bucket_index, cid, ease, ivl, lastIvl, _type in result:
        if ivl > 0 and lastIvl < 0 and cid not in first_learned:
            first_learned[cid] = _id

        # Any ids earlier than the cutoff will not be graphed.  We only queried them to determine the
        # first time each card was learned.
        if id_cutoff and _id < id_cutoff:
            continue

        key = (bucket_index, cid)
        review = CardReview(id=_id, first_learned_id=first_learned.get(cid),
                            bucket_index=bucket_index, cid=cid, ease=ease, ivl=ivl,
                            lastIvl=lastIvl, type=_type)
        card_reviews = all_reviews_for_bucket.get(key)
        if not card_reviews:
            card_reviews = CardReviewsForBucket(bucket_index=bucket_index, cid=cid, reviews=[])
            all_reviews_for_bucket[key] = card_reviews
        card_reviews.reviews.append(review)

    return all_reviews_for_bucket


def _has_matured(card_reviews, last_ivl):
    """Check if the card started the length of time as not mature and ended as mature."""

    # We compare the first and last reviews of the bucket.  If we counted each individual
    # review then this would overcount.  We don't care how many times the card reached
    # maturity during the interval.  We only care if the net change over the interval was
    # becoming mature.

    first_review = card_reviews.reviews[0]
    last_review = card_reviews.reviews[-1]

    # Prefer last_ivl if available because lastIvl isn't always correct (Anki bug?).
    if not last_ivl:
        last_ivl = first_review.lastIvl

    return last_ivl < 21 and last_review.ivl >= 21


def _num_matured(card_reviews):
    """Count the number of times the card matured over the length of time.
    This can be greater than one because the card may be forgotten and mature again."""

    tot = 0
    for review in card_reviews.reviews:
        if review.lastIvl < 21 and review.ivl >= 21:
            tot += 1

    return tot


def _has_lost_matured(card_reviews, last_ivl):
    "Check if the card has lost maturity for the current length of time."
    first_review = card_reviews.reviews[0]
    last_review = card_reviews.reviews[-1]

    # Prefer last_ivl if available because lastIvl isn't always correct (Anki bug?).
    if not last_ivl:
        last_ivl = first_review.lastIvl

    return last_ivl >= 21 and last_review.ivl < 21


def _has_learned(card_reviews):
    "Check if the card was learned at some point during the length of time."

    # We check each individual review rather than the first and last review of the bucket.
    # If we were to compare the first and last reviews this could give us the wrong result as
    # when the card is relearned the interval will drop below zero again.
    for review in card_reviews.reviews:
        # We assume the card is no longer being learned once the new interval is above zero.
        # Learning intervals are in seconds (which is expressed as a negative number).
        # Since a card can be relearned, we compare the id (which is a timestamp) to the id for the first
        # time the card was learned.  If they don't match then this isn't the first time the card was learned.
        # We don't use the type (which indicates learn, relearn, etc.) because it isn't reliable for filtered decks.
        if review.lastIvl < 0 and review.ivl > 0 and review.id == review.first_learned_id:
            return True

    return False


def _new_bucket_stats(bucket_index):
    return BucketStats(bucket_index=bucket_index, stats=ProgressStats())


def get_stats(db_table, bucket_size_days, day_cutoff_seconds, num_buckets=None, additional_filter=None):
    """Returns progress statistics bucketed by bucket_size_days.  The statistics are:

    matured_cards: number of cards that went from young to mature
    lost_matured_card: number of cards that went from mature to young
    net_matured_cards: the net increase in mature cards (matured_cards - lost_matured_card)
    matured_reviews: the number of reviews that yielded mature cards
    learned_cards: number of cards that exited the learning phase

    bucket_size_days represents the size of each bucket measusured in days.  So a value of 1 buckets per day,
    a value of 7 buckets per week, etc.

    day_cutoff_seconds is the cutoff measured in seconds since epoch for the start of the next day.  So, for example,
    if the cutoff is 4 am then this should be tomorrow at 4 am.

    num_buckets is the (optional) number of buckets, which indicates how many reviews to fetch.  Enough reviews are
    fetched to fill all the buckets.  So, for example, if bucket_size_days is 1 and num_buckets is 30 this fetches
    the last month of reviews.

    db_table is the table used to fetch from the review logs.

    additional_filter is an (optiona) filter added to the SQL WHERE clause that limits which reviews to fetch.
    This can be used to limit the reviews to a particular deck, for example.
    """

    stats_by_name = defaultdict(list)

    min_bucket_index = 0
    if num_buckets:
        min_bucket_index = -1 * num_buckets + 1
    max_bucket_index = 0

    all_reviews_for_bucket = _get_reviews(
        db_table, bucket_size_days, day_cutoff_seconds, num_buckets, additional_filter)

    # If there is no review data then return empty dictionary. No graphs should be plotted.
    if not all_reviews_for_bucket:
        return stats_by_name

    stats_by_bucket = {}
    last_ivl_by_cid = {}

    # sort by bucket
    for key in sorted(all_reviews_for_bucket, key=lambda k: k[0]):
        # Get reviews for a particular card in a particular bucket.
        # The key is (bucket_index, cid).
        card_reviews = all_reviews_for_bucket[key]

        bucket_index, cid = key

        last_ivl = last_ivl_by_cid.get(cid, 0)

        if bucket_index < min_bucket_index:
            min_bucket_index = bucket_index

        if bucket_index > max_bucket_index:
            max_bucket_index = bucket_index

        bucket_stats = stats_by_bucket.get(bucket_index)
        if not bucket_stats:
            bucket_stats = _new_bucket_stats(bucket_index)
            stats_by_bucket[bucket_index] = bucket_stats

        if _has_matured(card_reviews, last_ivl):
            bucket_stats.stats.matured_cards += 1

        bucket_stats.stats.matured_reviews += _num_matured(card_reviews)

        if _has_lost_matured(card_reviews, last_ivl):
            bucket_stats.stats.lost_matured_card += 1

        if _has_learned(card_reviews):
            bucket_stats.stats.learned_cards += 1

        last_ivl_by_cid[cid] = card_reviews.reviews[-1].ivl

    for bucket_index in range(min_bucket_index, max_bucket_index + 1):
        # Fill in days missing reviews with zero values
        if bucket_index not in stats_by_bucket:
            stats_by_bucket[bucket_index] = _new_bucket_stats(bucket_index)

        stats = stats_by_bucket[bucket_index]

        # The net increase in mature cards
        net_matured_cards = stats.stats.matured_cards - stats.stats.lost_matured_card

        stats_by_name["matured_cards"].append((bucket_index, stats.stats.matured_cards))
        stats_by_name["net_matured_cards"].append((bucket_index, net_matured_cards))
        stats_by_name["matured_reviews"].append((bucket_index, stats.stats.matured_reviews))
        stats_by_name["lost_matured_card"].append((bucket_index, stats.stats.lost_matured_card))
        stats_by_name["learned_cards"].append((bucket_index, stats.stats.learned_cards))

    return stats_by_name
