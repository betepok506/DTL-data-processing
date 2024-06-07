from shapely.geometry import Polygon
from shapely.ops import transform
from pyproj import Transformer


def transform_polygon(polygon: Polygon, from_crs: str, to_crs: str) -> Polygon:
    # Создание трансформера для преобразования координат
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)

    # Функция для преобразования координат
    def transform_coords(x, y):
        return transformer.transform(x, y)

    # Преобразование координат полигона
    transformed_polygon = transform(transform_coords, polygon)

    return transformed_polygon


'''
# Пример использования
# Создание полигона в системе координат EPSG:32637
polygon_epsg_32637 = Polygon([(500000, 4649776), (500100, 4649776), (500100, 4649676), (500000, 4649676), (500000, 4649776)])

# Преобразование полигона в систему координат EPSG:4326
polygon_epsg_4326 = transform_polygon(polygon_epsg_32637, "EPSG:32637", "EPSG:4326")
'''
