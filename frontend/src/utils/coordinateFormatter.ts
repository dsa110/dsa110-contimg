export const formatRA = (raDeg: number): string => {
  const hours = Math.floor(raDeg / 15);
  const minutes = Math.floor((raDeg % 15) * 4);
  const seconds = Math.round(((raDeg % 15) * 4 - minutes) * 60);
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
};

export const formatDec = (decDeg: number): string => {
  const degrees = Math.abs(Math.floor(decDeg));
  const minutes = Math.floor((Math.abs(decDeg) % 1) * 60);
  const seconds = Math.round(((Math.abs(decDeg) % 1) * 60 - minutes) * 60);
  const sign = decDeg >= 0 ? "+" : "-";
  return `${sign}${degrees.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
};
