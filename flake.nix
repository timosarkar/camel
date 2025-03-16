{
  description = "nix flake to build ocaml dune projects";

  inputs = {
    systems.url = "github:nix-systems/default";
  };

  outputs = { self, nixpkgs, systems }:
    let
      lib = nixpkgs.lib;
      eachSystem = lib.genAttrs (import systems);
    in
    {
      packages = eachSystem (system:
        let
          legacyPackages = nixpkgs.legacyPackages.${system};
          ocamlPackages = legacyPackages.ocamlPackages;
        in
        {
          default = self.packages.${system}.hello;

          hello = ocamlPackages.buildDunePackage {
            pname = "PLACEHOLDER_PROJECTNAME";
            version = "0.1.0";
            duneVersion = "3";
            src = ./.;

            buildInputs = [
              # OCaml package dependencies go here.
            ];

            strictDeps = true;
          };
        });

      devShells = eachSystem (system:
        let
          legacyPackages = nixpkgs.legacyPackages.${system};
          ocamlPackages = legacyPackages.ocamlPackages;
        in
        {
          default = legacyPackages.mkShell {
            packages = [
              legacyPackages.fswatch
              ocamlPackages.odoc
              ocamlPackages.ocaml-lsp
            ];

            inputsFrom = [
              self.packages.${system}.hello
            ];
          };
        });
    };
}
