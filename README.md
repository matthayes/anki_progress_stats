# Anki Progress Stats

This is a plugin for [Anki](http://ankisrs.net/) that adds the following graphs.  You can find it listed under [Anki addons](https://ankiweb.net/shared/addons/).

## Graphs

### Learned Cards

This is the number of cards that were learned.  A card is considered "learned" if it leaves the learning phase.  This ignores cards that were relearned.  This also plots the cumulative total.  When this is plotted over the deck lifetime, the final cumulative total roughly equals the number of young cards plus the number of matured cards minus the number of learned cards
that are suspended.

### Net Matured Cards

This is the net change in the number of matured cards, equal to the number of matured cards minus the number of cards that were mature but were forgotten.  A card is considered "matured" when its interval increases above 21 days and forgotten when its interval drop below 21 days.  This also plots the cumulative total.  When this is plotted over the deck lifetime, the final cumulative total roughly equals the number of matured cards minus the number of matured cards that are suspended.

### Matured Cards

This is the number of matured cards, as explained above.  This is included to help understand the values in the Net Matured Cards graph.

### Matured Cards Lost

This is the number of matured cards lost, as explained above.  This is included to help understand the values in the Net Matured Cards graph.

## Motivation

Anki includes a Review Count graph that plots the total reviews for learning, relearning, young, and mature cards.  This graph is great if you want to know how many reviews occurred in each category, but it can be difficult understand progress using it.  Since one of the goals is to learn cards and have them eventually matured, this plugin tracks statistics for that specifically.

## License

Copyright 2016 Matthew Hayes

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
