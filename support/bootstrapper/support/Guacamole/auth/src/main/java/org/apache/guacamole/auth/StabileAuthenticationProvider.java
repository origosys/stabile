package org.apache.guacamole.auth;

import java.util.Map;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.ArrayUtils;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.GuacamoleServerException;
import org.apache.guacamole.net.auth.simple.SimpleAuthenticationProvider;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.protocol.GuacamoleConfiguration;
import org.apache.guacamole.environment.Environment;
import org.apache.guacamole.environment.LocalEnvironment;
import java.util.HashMap;
import javax.servlet.http.HttpServletRequest;


import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.sql.*;
import java.util.logging.Logger;
import java.util.Properties;
import java.util.logging.Handler;
import java.util.logging.FileHandler;
import java.util.logging.Level;


/**
 * Authentication provider implementation intended to demonstrate basic use
 * of Guacamole's extension API. The credentials and connection information for
 * a single user are stored directly in guacamole.properties.
 */
public class StabileAuthenticationProvider extends SimpleAuthenticationProvider {
//    Handler fh = new FileHandler("/var/log/stabile/guac.log");
//    Logger.getLogger("").addHandler(fh);
//    Logger.getLogger("io.stabile").setLevel(Level.FINEST);

    private static Logger logger = Logger.getLogger("io.stabile");

    private Connection connect = null;
    private Statement statement = null;
    private ResultSet resultSet = null;
    String user;

    @Override
    public String getIdentifier() {
        return "stabile";
    }

    @Override
    public Map<String, GuacamoleConfiguration>
        getAuthorizedConfigurations(Credentials credentials)
        throws GuacamoleException {

        Handler fh = null;
        try {
            fh = new FileHandler("/var/log/tomcat8/guac.log");
        } catch (java.io.IOException exception) {
            exception.printStackTrace();
        }
        logger.addHandler(fh);
        logger.setLevel(Level.FINEST);

        HttpServletRequest request = credentials.getRequest();

        user = request.getHeader("STEAM_USER");
        String uuid = request.getParameter("uuid");
        String[] hostPort = null;
        if (user == null) {
            logger.info("Not allowing unauthenticated user");
            return null;
        } else if (uuid == null) {
            logger.info("No uuid specified");
            return null;
        } else {
            logger.info("Tunneling user: " + user);
        }
        try {
            hostPort = lookupHostPort(uuid);
        } catch (Exception e) {
            e.printStackTrace();
        }

        String hostname;
        String port;
        String password = request.getParameter("password");
        if (hostPort!=null && hostPort.length > 0) {
            hostname = hostPort[0];
            port = hostPort[1];

            // Successful login. Return configurations.
            Map<String, GuacamoleConfiguration> configs = new HashMap<String, GuacamoleConfiguration>();
            GuacamoleConfiguration config = new GuacamoleConfiguration();
            config.setProtocol("vnc");
            config.setParameter("hostname", hostname);
            config.setParameter("port", port);
            if (password != null && !password.equals("")) config.setParameter("password", password);
            logger.info("Opening display vnc://" + hostname + ":" + port);
            configs.put(" ", config);
            return configs;
        } else {
            logger.info("Could not lookup display for " + uuid + " to connect to");
            return null;
        }
    }

    public String[] lookupHostPort(String uuid) throws GuacamoleException {
        String host = null;
        String port = null;
        String dbuser = null;
        String privileges = null;
        String accounts = null;
        String accountsprivileges = null;
        String[] hostPort = new String[2];
        String dbi_user = null; //"irigo";
        String dbi_passwd = null; //"sunshine";
        try {

            Properties props = new java.util.Properties();
            try {
                InputStream is = new FileInputStream("/etc/stabile/config.cfg");
                props.load(is);
                //props.load(this.getClass().getClassLoader().getResourceAsStream("/etc/stabile/config.cfg"));
                dbi_user = props.getProperty("DBI_USER");
                dbi_passwd = props.getProperty("DBI_PASSWD");
            } catch (FileNotFoundException e) {
                e.printStackTrace();
            } catch (IOException e) {
                e.printStackTrace();
            } catch(Exception e){
                e.printStackTrace();
            }

            // This will load the MySQL driver, each DB has its own driver
            Class.forName("com.mysql.jdbc.Driver");
            Properties connectionProps = new Properties();
            connectionProps.put("user", dbi_user);
            connectionProps.put("password", dbi_passwd);
            // Setup the connection with the DB
            connect = DriverManager.getConnection("jdbc:mysql://localhost/steamregister", connectionProps);

            // Statements allow us to issue SQL queries to the database
            statement = connect.createStatement();
            // Result set get the result of the SQL query
            resultSet = statement.executeQuery("select * from domains where uuid = '" + uuid + "'");
            if (resultSet.next()) {
                dbuser = resultSet.getString("user");
                host = resultSet.getString("macip");
                port = resultSet.getString("port");
            }
            resultSet = statement.executeQuery("select * from users where username = '" + user + "'");
            if (resultSet.next()) {
                privileges = resultSet.getString("privileges");
                accounts = resultSet.getString("accounts");
                accountsprivileges = resultSet.getString("accountsprivileges");
            }
            close();
        } catch (Exception e) {
            logger.info("Failure connecting to DB:" + e.toString());
            throw new GuacamoleException(e);
        } finally {
            close();
        }
        if (privileges==null) privileges = "";
        if (accounts==null) accounts = "";
        if (accountsprivileges==null) accountsprivileges = "";

        String[] aarray;
        String[] parray;
        boolean allowaccess = false;
        aarray = accounts.split(",\\s*");
        parray = accountsprivileges.split(",\\s*");

        if (dbuser!=null && dbuser.equals(user) && !privileges.contains("d") && !privileges.contains("r")) {
            allowaccess = true;
        } else {
            int i=0;
            for (String s : aarray) {
                if (s.equals(dbuser)) {
                    if (i>=parray.length || (!parray[i].contains("d") && !parray[i].contains("r"))) {
                        allowaccess = true;
                    }
                    break;
                }
                i++;
            }
        }

        if (host!=null && !host.equals("") && port!=null && !port.equals("")) {
            if (allowaccess) {
                hostPort[0] = host;
                hostPort[1] = port;
            } else {
                logger.info("Security check failed: " + uuid + " cannot be accessed by " + user);
                throw new GuacamoleException("Security check failed: " + uuid + " cannot be accessed by " + user);
            }
        }
        return hostPort;
    }

    private void close() {
        try {
            if (resultSet != null) {
                resultSet.close();
            }

            if (statement != null) {
                statement.close();
            }

            if (connect != null) {
                connect.close();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static Map<String, String[]> getQueryParameters(HttpServletRequest request) {
        Map<String, String[]> queryParameters = new HashMap<String, String[]>();
        String queryString = request.getQueryString();

        if (StringUtils.isEmpty(queryString)) {
            return queryParameters;
        }

        String[] parameters = queryString.split("&");

        for (String parameter : parameters) {
            String[] keyValuePair = parameter.split("=");
            String[] values = queryParameters.get(keyValuePair[0]);
            values = ArrayUtils.add(values, keyValuePair.length == 1 ? "" : keyValuePair[1]); //length is one if no value is available.
            queryParameters.put(keyValuePair[0], values);
        }
        return queryParameters;
    }
}
