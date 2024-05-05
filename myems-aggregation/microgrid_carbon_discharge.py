import time
from datetime import datetime, timedelta
from decimal import Decimal
import mysql.connector
import carbon_dioxide_emmision_factor
import config


########################################################################################################################
# PROCEDURES
# Step 1: get all microgrids
# for each microgrid in list:
#   Step 2: get the latest start_datetime_utc
#   Step 3: get all discharge energy data since the latest start_datetime_utc
#   Step 4: get carbon dioxide emissions factor
#   Step 5: calculate discharge carbon dioxide emissions by multiplying energy with factor
#   Step 6: save discharge carbon dioxide emissions data to database
########################################################################################################################


def main(logger):

    while True:
        # the outermost while loop
        ################################################################################################################
        # Step 1: get all microgrids
        ################################################################################################################
        cnx_system_db = None
        cursor_system_db = None
        try:
            cnx_system_db = mysql.connector.connect(**config.myems_system_db)
            cursor_system_db = cnx_system_db.cursor()
        except Exception as e:
            logger.error("Error in step 1.1 of microgrid_carbon_discharge " + str(e))
            if cursor_system_db:
                cursor_system_db.close()
            if cnx_system_db:
                cnx_system_db.close()
            # sleep and continue the outermost while loop
            time.sleep(60)
            continue

        print("Connected to MyEMS System Database")

        microgrid_list = list()
        try:
            cursor_system_db.execute(" SELECT id, name, cost_center_id "
                                     " FROM tbl_microgrids "
                                     " ORDER BY id ")
            rows_microgrids = cursor_system_db.fetchall()

            if rows_microgrids is None or len(rows_microgrids) == 0:
                print("Step 1.2: There isn't any microgrids. ")
                if cursor_system_db:
                    cursor_system_db.close()
                if cnx_system_db:
                    cnx_system_db.close()
                # sleep and continue the outermost while loop
                time.sleep(60)
                continue

            for row in rows_microgrids:
                microgrid_list.append({"id": row[0], "name": row[1], "cost_center_id": row[2]})

        except Exception as e:
            logger.error("Error in step 1.2 of microgrid_carbon_discharge " + str(e))
            if cursor_system_db:
                cursor_system_db.close()
            if cnx_system_db:
                cnx_system_db.close()
            # sleep and continue the outermost while loop
            time.sleep(60)
            continue

        print("Step 1.2: Got all microgrids from MyEMS System Database")

        cnx_energy_db = None
        cursor_energy_db = None
        try:
            cnx_energy_db = mysql.connector.connect(**config.myems_energy_db)
            cursor_energy_db = cnx_energy_db.cursor()
        except Exception as e:
            logger.error("Error in step 1.3 of microgrid_carbon_discharge " + str(e))
            if cursor_energy_db:
                cursor_energy_db.close()
            if cnx_energy_db:
                cnx_energy_db.close()

            if cursor_system_db:
                cursor_system_db.close()
            if cnx_system_db:
                cnx_system_db.close()
            # sleep and continue the outermost while loop
            time.sleep(60)
            continue

        print("Connected to MyEMS Energy Database")

        cnx_carbon_db = None
        cursor_carbon_db = None
        try:
            cnx_carbon_db = mysql.connector.connect(**config.myems_carbon_db)
            cursor_carbon_db = cnx_carbon_db.cursor()
        except Exception as e:
            logger.error("Error in step 1.4 of microgrid_carbon_discharge " + str(e))
            if cursor_carbon_db:
                cursor_carbon_db.close()
            if cnx_carbon_db:
                cnx_carbon_db.close()

            if cursor_energy_db:
                cursor_energy_db.close()
            if cnx_energy_db:
                cnx_energy_db.close()

            if cursor_system_db:
                cursor_system_db.close()
            if cnx_system_db:
                cnx_system_db.close()
            # sleep and continue the outermost while loop
            time.sleep(60)
            continue

        print("Connected to MyEMS Carbon Database")

        for microgrid in microgrid_list:
            ############################################################################################################
            # Step 2: get the latest start_datetime_utc
            ############################################################################################################
            print("Step 2: get the latest start_datetime_utc from carbon database for " + microgrid['name'])
            try:
                cursor_carbon_db.execute(" SELECT MAX(start_datetime_utc) "
                                         " FROM tbl_microgrid_discharge_hourly "
                                         " WHERE microgrid_id = %s ",
                                         (microgrid['id'], ))
                row_datetime = cursor_carbon_db.fetchone()
                start_datetime_utc = datetime.strptime(config.start_datetime_utc, '%Y-%m-%d %H:%M:%S')
                start_datetime_utc = start_datetime_utc.replace(minute=0, second=0, microsecond=0, tzinfo=None)

                if row_datetime is not None and len(row_datetime) > 0 and isinstance(row_datetime[0], datetime):
                    # replace second and microsecond with 0
                    # note: do not replace minute in case of calculating in half hourly
                    start_datetime_utc = row_datetime[0].replace(second=0, microsecond=0, tzinfo=None)
                    # start from the next time slot
                    start_datetime_utc += timedelta(minutes=config.minutes_to_count)

                print("start_datetime_utc: " + start_datetime_utc.isoformat()[0:19])
            except Exception as e:
                logger.error("Error in step 2 of microgrid_carbon_discharge " + str(e))
                # break the for microgrid loop
                break

            ############################################################################################################
            # Step 3: get all discharge energy data since the latest start_datetime_utc
            ############################################################################################################
            print("Step 3: get all discharge energy data since the latest start_datetime_utc")

            query = (" SELECT start_datetime_utc, actual_value "
                     " FROM tbl_microgrid_discharge_hourly "
                     " WHERE microgrid_id = %s AND start_datetime_utc >= %s "
                     " ORDER BY id ")
            cursor_energy_db.execute(query, (microgrid['id'], start_datetime_utc, ))
            rows_hourly = cursor_energy_db.fetchall()

            if rows_hourly is None or len(rows_hourly) == 0:
                print("Step 3: There isn't any discharge energy data to calculate. ")
                # continue the for microgrid loop
                continue

            energy_dict = dict()
            end_datetime_utc = start_datetime_utc
            for row_hourly in rows_hourly:
                current_datetime_utc = row_hourly[0]
                actual_value = row_hourly[1]
                energy_dict[current_datetime_utc] = actual_value
                if current_datetime_utc > end_datetime_utc:
                    end_datetime_utc = current_datetime_utc

            ############################################################################################################
            # Step 4: get carbon dioxide emissions factor
            ############################################################################################################
            print("Step 4: get carbon dioxide emissions factor")
            factor_dict = dict()
            factor_dict[1] = \
                carbon_dioxide_emmision_factor.get_energy_category_factor(
                    1,
                    start_datetime_utc,
                    end_datetime_utc)
            ############################################################################################################
            # Step 5: calculate carbon dioxide emissions by multiplying energy with factor
            ############################################################################################################
            print("Step 5: calculate carbon dioxide emissions by multiplying energy with factor")
            carbon_dict = dict()

            if len(energy_dict) > 0:
                for current_datetime_utc in energy_dict.keys():
                    current_factor = factor_dict[1]
                    current_energy = energy_dict[current_datetime_utc]
                    if current_factor is not None \
                            and isinstance(current_factor, Decimal) \
                            and current_energy is not None \
                            and isinstance(current_energy, Decimal):
                        carbon_dict[current_datetime_utc] = current_energy * current_factor

            ############################################################################################################
            # Step 6: save carbon dioxide emissions data to database
            ############################################################################################################
            print("Step 6: save carbon dioxide emissions data to database")

            if len(carbon_dict) > 0:
                try:
                    add_values = (" INSERT INTO tbl_microgrid_discharge_hourly "
                                  "             (microgrid_id, "
                                  "              start_datetime_utc, "
                                  "              actual_value) "
                                  " VALUES  ")

                    for current_datetime_utc in carbon_dict:
                        current_carbon = carbon_dict[current_datetime_utc]
                        if current_carbon is not None and isinstance(current_carbon, Decimal):
                            add_values += " (" + str(microgrid['id']) + ","
                            add_values += "'" + current_datetime_utc.isoformat()[0:19] + "',"
                            add_values += str(current_carbon) + "), "

                    print("add_values:" + add_values)
                    # trim ", " at the end of string and then execute
                    cursor_carbon_db.execute(add_values[:-2])
                    cnx_carbon_db.commit()
                except Exception as e:
                    logger.error("Error in step 6 of microgrid_carbon_discharge " + str(e))
                    # break the for microgrid loop
                    break

        # end of for microgrid loop
        if cursor_system_db:
            cursor_system_db.close()
        if cnx_system_db:
            cnx_system_db.close()

        if cursor_energy_db:
            cursor_energy_db.close()
        if cnx_energy_db:
            cnx_energy_db.close()

        if cursor_carbon_db:
            cursor_carbon_db.close()
        if cnx_carbon_db:
            cnx_carbon_db.close()
        print("go to sleep 300 seconds...")
        time.sleep(300)
        print("wake from sleep, and continue to work...")
    # end of the outermost while loop
