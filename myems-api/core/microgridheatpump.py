import uuid
import falcon
import mysql.connector
import simplejson as json
from core.useractivity import user_logger, admin_control, access_control
import config


class MicrogridHeatpumpCollection:
    @staticmethod
    def __init__():
        """Initializes MicrogridHeatpumpCollection"""
        pass

    @staticmethod
    def on_options(req, resp):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp):
        access_control(req)
        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        # query microgrid dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_microgrids ")
        cursor.execute(query)
        rows_microgrids = cursor.fetchall()

        microgrid_dict = dict()
        if rows_microgrids is not None and len(rows_microgrids) > 0:
            for row in rows_microgrids:
                microgrid_dict[row[0]] = {"id": row[0],
                                          "name": row[1],
                                          "uuid": row[2]}
        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, microgrid_id, "
                 "        power_point_id, electricity_meter_id, heat_meter_id, cooling_meter_id, capacity "
                 " FROM tbl_microgrids_heatpumps "
                 " ORDER BY id ")
        cursor.execute(query)
        rows_microgrid_heatpumps = cursor.fetchall()

        result = list()
        if rows_microgrid_heatpumps is not None and len(rows_microgrid_heatpumps) > 0:
            for row in rows_microgrid_heatpumps:
                microgrid = microgrid_dict.get(row[3])
                power_point = point_dict.get(row[4])
                electricity_meter = meter_dict.get(row[5])
                heat_meter = meter_dict.get(row[6])
                cooling_meter = meter_dict.get(row[7])
                meta_result = {"id": row[0],
                               "name": row[1],
                               "uuid": row[2],
                               "microgrid": microgrid,
                               "power_point": power_point,
                               "electricity_meter": electricity_meter,
                               "heat_meter": heat_meter,
                               "cooling_meter": cooling_meter,
                               "capacity": row[8]}
                result.append(meta_result)

        cursor.close()
        cnx.close()
        resp.text = json.dumps(result)

    @staticmethod
    @user_logger
    def on_post(req, resp):
        """Handles POST requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_MICROGRID_HEATPUMP_NAME')
        name = str.strip(new_values['data']['name'])

        if 'microgrid_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['microgrid_id'], int) or \
                new_values['data']['microgrid_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_MICROGRID_ID')
        microgrid_id = new_values['data']['microgrid_id']

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'electricity_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['electricity_meter_id'], int) or \
                new_values['data']['electricity_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ELECTRICITY_METER_ID')
        electricity_meter_id = new_values['data']['electricity_meter_id']

        if 'heat_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['heat_meter_id'], int) or \
                new_values['data']['heat_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_SELL_METER_ID')
        heat_meter_id = new_values['data']['heat_meter_id']

        if 'cooling_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['cooling_meter_id'], int) or \
                new_values['data']['cooling_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_COOLING_METER_ID')
        cooling_meter_id = new_values['data']['cooling_meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_microgrids "
                       " WHERE id = %s ",
                       (microgrid_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.MICROGRID_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_microgrids_heatpumps "
                       " WHERE microgrid_id = %s AND name = %s ",
                       (microgrid_id, name,))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.MICROGRID_HEATPUMP_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (electricity_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ELECTRICITY_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (heat_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.HEAT_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (cooling_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.COOLING_METER_NOT_FOUND')

        add_values = (" INSERT INTO tbl_microgrids_heatpumps "
                      "    (name, uuid, microgrid_id, power_point_id, heat_meter_id, cooling_meter_id, capacity) "
                      " VALUES (%s, %s, %s, %s, %s, %s, %s) ")
        cursor.execute(add_values, (name,
                                    str(uuid.uuid4()),
                                    microgrid_id,
                                    power_point_id,
                                    electricity_meter_id,
                                    heat_meter_id,
                                    cooling_meter_id,
                                    capacity))
        new_id = cursor.lastrowid
        cnx.commit()
        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_201
        resp.location = '/microgridheatpumps/' + str(new_id)


class MicrogridHeatpumpItem:
    @staticmethod
    def __init__():
        """Initializes MicrogridHeatpumpItem"""
        pass

    @staticmethod
    def on_options(req, resp, id_):
        resp.status = falcon.HTTP_200

    @staticmethod
    def on_get(req, resp, id_):
        access_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_MICROGRID_HEATPUMP_ID')

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        # query microgrid dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_microgrids ")
        cursor.execute(query)
        rows_microgrids = cursor.fetchall()

        microgrid_dict = dict()
        if rows_microgrids is not None and len(rows_microgrids) > 0:
            for row in rows_microgrids:
                microgrid_dict[row[0]] = {"id": row[0],
                                          "name": row[1],
                                          "uuid": row[2]}
        # query meter dict
        query = (" SELECT id, name, uuid "
                 " FROM tbl_meters ")
        cursor.execute(query)
        rows_meters = cursor.fetchall()

        meter_dict = dict()
        if rows_meters is not None and len(rows_meters) > 0:
            for row in rows_meters:
                meter_dict[row[0]] = {"id": row[0],
                                      "name": row[1],
                                      "uuid": row[2]}
        # query point dict
        query = (" SELECT id, name "
                 " FROM tbl_points ")
        cursor.execute(query)
        rows_points = cursor.fetchall()

        point_dict = dict()
        if rows_points is not None and len(rows_points) > 0:
            for row in rows_points:
                point_dict[row[0]] = {"id": row[0],
                                      "name": row[1]}

        query = (" SELECT id, name, uuid, microgrid_id, "
                 "        power_point_id, electricity_meter_id, heat_meter_id, cooling_meter_id, capacity "
                 " FROM tbl_microgrids_heatpumps "
                 " WHERE id = %s ")
        cursor.execute(query, (id_,))
        row = cursor.fetchone()
        cursor.close()
        cnx.close()

        if row is None:
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.MICROGRID_HEATPUMP_NOT_FOUND')
        else:
            microgrid = microgrid_dict.get(row[3])
            power_point = point_dict.get(row[4])
            electricity_meter = meter_dict.get(row[5])
            heat_meter = meter_dict.get(row[6])
            cooling_meter = meter_dict.get(row[7])
            meta_result = {"id": row[0],
                           "name": row[1],
                           "uuid": row[2],
                           "microgrid": microgrid,
                           "power_point": power_point,
                           "electricity_meter": electricity_meter,
                           "heat_meter": heat_meter,
                           "cooling_meter": cooling_meter,
                           "capacity": row[8]}

        resp.text = json.dumps(meta_result)

    @staticmethod
    @user_logger
    def on_delete(req, resp, id_):
        admin_control(req)
        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_MICROGRID_HEATPUMP_ID')
        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_microgrids_heatpumps "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.MICROGRID_HEATPUMP_NOT_FOUND')

        cursor.execute(" DELETE FROM tbl_microgrids_heatpumps "
                       " WHERE id = %s ", (id_,))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_204

    @staticmethod
    @user_logger
    def on_put(req, resp, id_):
        """Handles PUT requests"""
        admin_control(req)
        try:
            raw_json = req.stream.read().decode('utf-8')
        except Exception as ex:
            raise falcon.HTTPError(status=falcon.HTTP_400,
                                   title='API.BAD_REQUEST',
                                   description='API.FAILED_TO_READ_REQUEST_STREAM')

        if not id_.isdigit() or int(id_) <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_MICROGRID_HEATPUMP_ID')

        new_values = json.loads(raw_json)

        if 'name' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['name'], str) or \
                len(str.strip(new_values['data']['name'])) == 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_MICROGRID_HEATPUMP_NAME')
        name = str.strip(new_values['data']['name'])

        if 'microgrid_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['microgrid_id'], int) or \
                new_values['data']['microgrid_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_MICROGRID_ID')
        microgrid_id = new_values['data']['microgrid_id']

        if 'power_point_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['power_point_id'], int) or \
                new_values['data']['power_point_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_POWER_POINT_ID')
        power_point_id = new_values['data']['power_point_id']

        if 'electricity_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['electricity_meter_id'], int) or \
                new_values['data']['electricity_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ELECTRICITY_METER_ID')
        electricity_meter_id = new_values['data']['electricity_meter_id']

        if 'heat_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['heat_meter_id'], int) or \
                new_values['data']['heat_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_HEAT_METER_ID')
        heat_meter_id = new_values['data']['heat_meter_id']

        if 'cooling_meter_id' not in new_values['data'].keys() or \
                not isinstance(new_values['data']['cooling_meter_id'], int) or \
                new_values['data']['cooling_meter_id'] <= 0:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_COOLING_METER_ID')
        cooling_meter_id = new_values['data']['cooling_meter_id']

        if 'capacity' not in new_values['data'].keys() or \
                not (isinstance(new_values['data']['capacity'], float) or
                     isinstance(new_values['data']['capacity'], int)):
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_CAPACITY')
        capacity = float(new_values['data']['capacity'])

        cnx = mysql.connector.connect(**config.myems_system_db)
        cursor = cnx.cursor()

        cursor.execute(" SELECT name "
                       " FROM tbl_microgrids "
                       " WHERE id = %s ",
                       (microgrid_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.MICROGRID_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_microgrids_heatpumps "
                       " WHERE id = %s ", (id_,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.MICROGRID_HEATPUMP_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_microgrids_heatpumps "
                       " WHERE microgrid_id = %s AND name = %s AND id != %s ",
                       (microgrid_id, name, id_))
        if cursor.fetchone() is not None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.MICROGRID_HEATPUMP_NAME_IS_ALREADY_IN_USE')

        cursor.execute(" SELECT name "
                       " FROM tbl_points "
                       " WHERE id = %s ",
                       (power_point_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.POWER_POINT_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (electricity_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ELECTRICITY_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (heat_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.HEAT_METER_NOT_FOUND')

        cursor.execute(" SELECT name "
                       " FROM tbl_meters "
                       " WHERE id = %s ",
                       (cooling_meter_id,))
        if cursor.fetchone() is None:
            cursor.close()
            cnx.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.COOLING_METER_NOT_FOUND')

        update_row = (" UPDATE tbl_microgrids_heatpumps "
                      " SET name = %s, microgrid_id = %s, "
                      "     power_point_id = %s, electricity_meter_id = %s, heat_meter_id = %s, cooling_meter_id = %s, "
                      "     capacity = %s "
                      " WHERE id = %s ")
        cursor.execute(update_row, (name,
                                    microgrid_id,
                                    power_point_id,
                                    electricity_meter_id,
                                    heat_meter_id,
                                    heat_meter_id,
                                    capacity,
                                    id_))
        cnx.commit()

        cursor.close()
        cnx.close()

        resp.status = falcon.HTTP_200
