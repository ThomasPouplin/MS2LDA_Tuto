import java.util.ArrayList;
import java.io.*;
public class PeakList {
	private ArrayList<Peak> peaks;
	public PeakList() {
		peaks = new ArrayList<Peak>();
	}
	
	public Peak getPeak(int index) {
		return peaks.get(index);
	}
	public void addPeak(Peak p) {
		peaks.add(p);
	}
	public int getSize() {
		return peaks.size();
	}
	public int indexOf(Peak p) {
		int index = -1;
		for(int i=0;i<peaks.size();i++) {
			if(peaks.get(i).peakEquals(p)) {
				index = i;
				break;
			}
		}
		return index;
	}
	public void loadFromFile(String fName) {
		try {
			BufferedReader reader = new BufferedReader(new FileReader(fName));
			String temp = reader.readLine(); // Remove headings
			while((temp = reader.readLine())!=null) {
				String[] split = temp.split(",");
				String[] andsplit = split[3].split(";");
				peaks.add(new Peak(Double.parseDouble(split[0]),Double.parseDouble(split[1]),
						Double.parseDouble(split[2]),andsplit[0],andsplit[1],andsplit[2],Double.parseDouble(split[4])));
			}
			reader.close();
		}catch(IOException e) {
			System.out.println("Unable to load " + fName);
		}
	}
}
