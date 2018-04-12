#parse through the constants file to get the name of the database
dbname=$(cat ~/piaware-alerts/constants.py | grep "db_name" | cut -d'"' -f 2)
#get the date
today=$(date +%Y-%m-%d)
#create a copy of today's database with the date prepended to it
cp ~/piaware-alerts/${dbname} ~/piaware-alerts/${today}${dbname}
#upload the copied database
curl -T ~/piaware-alerts/${today}${dbname} ftp://192.168.1.165 --user ftpuser:ftppassword
#delete the copy we had just created
rm ~/piaware-alerts/${today}${dbname}
