# Octopus Agile Export

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

A Home Assistant integration that provides half-hourly pricing data for Octopus Energy Agile Export tariffs.

The integration is designed mainly to support automations that make use of export pricing data. The single main sensor displays the current price, but extra attributes on the sensor provide:

* A list of today's price slots (as a dictionary).
* A list of tomorrow's price slots (as a dictionary).
* The current price slot.

With some custom template sensors layered on top of this, you can do things like:

* Decide whether to use solar PV to charge a battery or export.
* Decide when to discharge a battery to the grid to maximise profit.
* Decide to run power-hungry devices at times of low export prices.

## Installation

This integration is delivered as a HACS custom repository.

1. Download and install [HACS][hacs-download].
2. Add a [custom repository][hacs-custom] in HACS. You will need to enter the URL of this repository when prompted: `https://github.com/cdpuk/octopus-export`.

## Configuration

When adding the integration you'll be prompted for your Distribution Network Operator (DNO) region. Agile pricing varies across the country, so it's important to choose the correct region to receive accurate data.

You can make a best guess based on the region names, but the best way is to read digits 9 and 10 from your MPAN (as seen on your bill). The map on to the options displayed on the configuration screen.

## Example template YAML

The following examples might be useful for creating advanced template sensors using `template.yaml` in your `config` directory.

### Find the most profitable evening slots

Useful for discharging a battery at the best time to optimise profit.

This particular example finds the 3 best slots between 16:00 and midnight, then computes a binary value `in_top_slot` which will be `true` if we're currently in one of those slots.

This might be combined with additional logic to work out whether you're better off keeping hold of battery charge until the next day.

```yaml
- binary_sensor:
    name: Discharge for profit (PM)
    icon: mdi:cash
    state: >
      {% set rates_today = state_attr('sensor.agile_export_rate', 'rates_today') %}
      {% set sorted_rates_today_pm = dict((rates_today.items() | list)[16*2:24*2]) | dictsort(by='value') %}
      {% set top_slots_today_pm = (dict(sorted_rates_today_pm).keys() | list)[-3:] %}
      {% set current_slot = state_attr('sensor.agile_export_rate', 'current_slot') %}
      {% set in_top_slot = current_slot in top_slots_today_pm %}

      {% if sufficient_profit and discharge_slots > 0 and in_top_slot -%}
        on
      {%- else -%}
        off
      {%- endif %}
```

### Estimate daytime export rate

This example takes an average of the export rates in the middle of the day tomorrow (between 12:00 and 16:00) as a rough attempt work out what we might get for suplus energy tomorrow.

Combined with the above example, this can be used to work out whether you're better off discharging a battery in the evening, or saving it until the next day.

```yaml
- sensor:
    name: Charging opportunity cost tomorrow
    unit_of_measurement: £/kWh
    icon: mdi:cash
    state: >
      {% set rates_tomorrow = state_attr('sensor.agile_export_rate', 'rates_tomorrow') %}
      {% if rates_tomorrow | count > 0 %}
        {{ (rates_tomorrow.values() | list)[12*2:16*2-1] | average | round(4) }}
      {% else %}
        unavailable
      {% endif %}
```

## Contributing

If you want to contribute to this please read the [Contribution Guidelines](CONTRIBUTING.md).

[commits-shield]: https://img.shields.io/github/commit-activity/y/cdpuk/octopus-export.svg?style=for-the-badge
[commits]: https://github.com/cdpuk/octopus-export/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/cdpuk/octopus-export.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/cdpuk/octopus-export.svg?style=for-the-badge
[releases]: https://github.com/cdpuk/octopus-export/releases
[hacs-download]: https://hacs.xyz/docs/setup/download
[hacs-custom]: https://hacs.xyz/docs/faq/custom_repositories
