import java.io.*;
import java.util.ArrayList;
public class ParseIDFiles {
	private String dataDir,outName;
	private ArrayList<PeakList> allLists;
	private ArrayList<String> shortName;
	private PeakList done;
	public ParseIDFiles(String directory,String o) {
		dataDir = directory;
		allLists = new ArrayList<PeakList>();
		shortName = new ArrayList<String>();
		outName = o;
		done = new PeakList();
		File[] fileList = new File(dataDir).listFiles();
		for(int i=0;i<fileList.length;i++) {
			System.out.println(fileList[i].getAbsolutePath());
			PeakList pl = new PeakList();
			pl.loadFromFile(fileList[i].getAbsolutePath());
			allLists.add(pl);
			String[] split = fileList[i].getAbsolutePath().split(File.separator);
			shortName.add(split[split.length-1]);
		}
		
		try {
			BufferedWriter writer = new BufferedWriter(new FileWriter(outName));
			String line = "DatabaseID,Adduct,Annotation";
			for(int i=0;i<shortName.size();i++) {
				line += "," + shortName.get(i);
			}
			writer.write(line + "\n");
			for(int i=0;i<allLists.size();i++) {
				for(int j=0;j<allLists.get(i).getSize();j++) {
					Peak temp = allLists.get(i).getPeak(j);
					if(temp.allC12() && temp.allO16() && temp.allN14() && temp.allS32() && temp.allSe80()) {
						// Compare with done
						boolean isDone = false;
						if(done.indexOf(temp) > -1) {
							isDone = true;
						}
						if(!isDone) {
							line = "";
							line += temp.getDatabaseID() + "," + temp.getAdduct() + "," + temp.getNotation();
							for(int k=0;k<allLists.size();k++) {
								line += ",";
								int index = allLists.get(k).indexOf(temp);
								if(index > -1) {
									line += ""+allLists.get(k).getPeak(index).getIntensity();
								}
							}
							done.addPeak(temp);
							System.out.println(line);
							writer.write(line + "\n");
						}
					}
				}
			}
			writer.close();
		}catch(IOException e) {
			System.out.println("Can't open output file");
		}
		
	}
	
	public static void main(String[] args) {
		String directory = "/Users/simonrogers/git/metabolomics_tools/AdductLevels/data/positive/std1/";
		ParseIDFiles p = new ParseIDFiles(directory,"std1pos.csv");
		
	}
}
