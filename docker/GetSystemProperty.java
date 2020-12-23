import java.util.Properties;
import java.util.Enumeration;

public class GetSystemProperty {
  public static void main(String args[]) {
    if( args.length == 0 ) {
      Properties p = System.getProperties();
      Enumeration keys = p.keys();
      while (keys.hasMoreElements()) {
        String key = (String)keys.nextElement();
        String value = (String)p.get(key);
        System.out.println(key + " : " + value);
      }
    }
    else {
      for (String key: args) {
        System.out.println(System.getProperty( key ));
      }
    }
  }
}
