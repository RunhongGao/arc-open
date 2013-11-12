from arcpy import AddMessage
import arcpy, csv, os, zipfile, glob, copy
from xml.dom.minidom import parse


class Export:

    def __init__(self, path, output_name, debug):
        self.path = path
        self.output_name = output_name
        self.full_path = self.path + '\\' + self.output_name
        self.shapefile = path + '\\shapefile\\' + output_name + '.shp'
        self.desc = arcpy.Describe(self.shapefile)
        self.fields = [i.name for i in arcpy.ListFields(self.shapefile)]
        self.debug = debug

    def __str__(self):
        return 'ArcOpen Export class'

    def _load(self, xml_file):
        xmldoc = parse(xml_file).documentElement
        return xmldoc

    def _print_title(self, xml):
        title = xml.getElementsByTagName('title')[0]
        title = title.firstChild.nodeValue
        return '# ' + title

    def _print_data_dict(self, fields):

        md = '### Data Dictionary\n\n'
        md += '| Field | Description  \n'
        md += '| ----- | :----------:  \n'
        for field in fields:
            md += '| ' + field + ' |  \n'
        return md

    def _print_section(self, section):
        elem, title = section
        try:
            content = self.source.getElementsByTagName(elem)[0]
            content = content.firstChild.nodeValue
            content = content.replace('\n', '  \n')
            md = '\n\n' + '### ' + title + '  \n\n'
            md += content
        except:
            pass

        return md.encode('ascii', 'ignore')

    def csv(self):
        shapefile_type = self.desc.shapeType

        try:
            if shapefile_type in ['Point', 'MultiPoint']:
                with open(self.full_path + '.csv', 'wb') as f:
                    writer = csv.writer(f)
                    try:
                        self.fields.remove('Shape')
                        self.fields.remove('FID')
                    except:
                        pass
                    headers = copy.deepcopy(self.fields)
                    self.fields.append('SHAPE@XY')
                    headers.extend(['LNG', 'LAT'])
                    writer.writerow(headers)
                    cur = arcpy.SearchCursor(self.shapefile)
                    with arcpy.da.SearchCursor(self.shapefile, self.fields) as cur:
                        for row in cur:
                            row = row[0:-1] + row[-1]
                            writer.writerow(row)
                    return True

            else:
                AddMessage('Sorry, converting layers of geometry type ' + shapefile_type + ' is not supported.')
                return False

        except Exception as err:
            AddMessage('Unable to export CSV file: ' + str(err))
            return False

    def zip(self):
        match = self.path + '\\shapefile\\' + self.output_name + '.*'
        zip_file = self.path + '\\shapefile\\' + self.output_name + '.zip'

        files = glob.glob(match)
        zf = zipfile.ZipFile(zip_file, mode='w')
        for file in files:
            try:
                zf.write(file, compress_type=zipfile.ZIP_DEFLATED, arcname=os.path.basename(file))
            except:
                AddMessage('Could not include ' + file + ' in .zip archive!')
                return False
        zf.close()
        return True

    def kmz(self):
        kmz_file = self.full_path + '.kmz'
        print 'KMZ path: ' + kmz_file
        arcpy.MakeFeatureLayer_management(self.shapefile, self.output_name)
        print 'Feature layer made: ' + self.output_name
        if arcpy.Exists(kmz_file):
            arcpy.Delete_management(kmz_file)
        try:
            arcpy.LayerToKML_conversion(self.output_name, kmz_file, '', '', self.output_name, '1024', '96', 'CLAMPED_TO_GROUND')
            return True
        except Exception as err:
            AddMessage('Unable to export KMZ file: ' + str(err))
            return False

    def md(self):
        install_dir = arcpy.GetInstallInfo('desktop')['InstallDir']
        # TODO: make sure translator file exists on the machine
        translator = install_dir + 'Metadata\\Translator\\ARCGIS2FGDC.xml'
        metadata = self.path + '\\shapefile\\temp\\README.xml'
        arcpy.ESRITranslator_conversion(self.shapefile, translator, metadata)

        top_sections = [
            ('purpose', 'Summary'),
            ('abstract', 'Description')
        ]
        bottom_sections = [
            ('datacred', 'Credits'),
            ('useconst', 'Use Limitations')
        ]
        self.source = self._load(metadata)
        metadata_fields = copy.deepcopy(self.fields)
        AddMessage(metadata_fields)
        metadata_fields.remove('SHAPE@XY')
        AddMessage(metadata_fields)
        self.markdown = ''

        self.markdown = self._print_title(self.source)

        for section in top_sections:
            self.markdown += self._print_section(section)

        self.markdown += '  \n\n'

        self.markdown += self._print_data_dict(metadata_fields)

        for section in bottom_sections:
            self.markdown += self._print_section(section)

        try:
            md_file = open(self.path + '\\README.md', 'w')
            md_file.write(self.markdown)
            return True
        except:
            return False
        finally:
            md_file.close()




