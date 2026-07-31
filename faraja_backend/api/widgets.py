"""
Custom Django admin widgets for map-based location picking.
"""
import json
from django import forms
from django.utils.html import format_html


class LocationMapWidget(forms.Widget):
    """
    A Django widget that displays a Leaflet map for picking a GeoJSON Point location.
    Stores location as: {"type": "Point", "coordinates": [longitude, latitude]}
    """
    template_name = 'admin/widgets/location_map.html'

    def get_context(self, name, value, attrs):
        """Prepare context for the widget template"""
        context = super().get_context(name, value, attrs)

        lat = 0
        lon = 0
        if value:
            try:
                # GEOSGeometry Point (from PointField)
                if hasattr(value, 'x') and hasattr(value, 'y'):
                    lon, lat = value.x, value.y
                elif isinstance(value, str):
                    data = json.loads(value)
                    if isinstance(data, dict) and data.get('type') == 'Point':
                        coords = data.get('coordinates', [])
                        if len(coords) == 2:
                            lon, lat = coords[0], coords[1]
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        context['widget'].update({
            'latitude': lat,
            'longitude': lon,
            'map_id': f'map_{name}_{id(self)}',
            'input_id': f'id_{name}',
        })
        
        return context

    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
            )
        }
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
            'admin/js/location_map_widget.js',
        )
